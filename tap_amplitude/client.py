"""REST client handling, including AmplitudeStream base class."""
import base64
import requests
import gzip
from pathlib import Path
from typing import Any, Dict, Optional, Iterable, cast
from io import BytesIO
from zipfile import ZipFile
from datetime import datetime, timedelta

import orjson
import pendulum
import urllib.parse

from singer_sdk.streams import RESTStream
from singer_sdk.authenticators import BasicAuthenticator
from singer_sdk.exceptions import RetriableAPIError


# Local file header signature for a non-empty zip; an empty archive starts
# with PK\x05\x06 (end-of-central-dir) but Amplitude's Export endpoint
# returns 404 + "Raw data files were not found" for empty windows, so we
# never expect a valid empty zip on a 200 response.
ZIP_MAGIC = b"PK\x03\x04"


def looks_like_zip(content: bytes) -> bool:
    """Return True if `content` starts with the standard ZIP magic bytes."""
    return content[:4] == ZIP_MAGIC


class AmplitudeStream(RESTStream):
    """Amplitude stream class."""
    
    AMPLITUDE_DATETIME_FORMAT = "%Y%m%dT%H"

    @property
    def url_base(self) -> str:
        if self.config.get("is_eu_region") == True:
            return "https://analytics.eu.amplitude.com/api/2/"
        return "https://amplitude.com/api/2/"

    @property
    def authenticator(self) -> BasicAuthenticator:
        """Return a new authenticator object."""
        return BasicAuthenticator.create_for_stream(
            self,
            username=self.config.get("api_key"),
            password=self.config.get("secret_key"),
        )

    def start_date(self, context: Optional[dict] = None):
        resolved = self._resolve_start_date(context)

        # Floor against min_start_date if configured. Hotglue's
        # override_start_date rewrites config.start_date and wipes state,
        # which can rewind syncs by months. min_start_date is an ordinary
        # config field the runtime does not touch, so it survives the
        # rewrite and clamps the effective start forward.
        floor = self.config.get("min_start_date")
        if floor:
            floor_dt = pendulum.parse(floor)
            if resolved < floor_dt:
                return floor_dt
        return resolved

    def _resolve_start_date(self, context: Optional[dict] = None):
        if self.replication_key:
            state = self.get_context_state(context)

            # Finalized bookmark from a clean prior run.
            finalized = state.get("replication_key_value")
            if finalized and state.get("replication_key") == self.replication_key:
                return pendulum.parse(finalized)

            # Resume point from a prior run that crashed before finalizing.
            # Without this, an interrupted sync forces the next run back to
            # config.start_date and we re-fetch everything from scratch.
            progress = state.get("progress_markers", {})
            in_flight = progress.get("replication_key_value")
            if in_flight and progress.get("replication_key") == self.replication_key:
                return pendulum.parse(in_flight)

        if self.config.get("start_date"):
            return pendulum.parse(self.config.get("start_date"))

        return pendulum.parse("2020-01-01T00:00:00.000Z")
    
    @property
    def window(self):
        return self.config.get("window_days")

    @property
    def http_headers(self) -> dict:
        """Return the http headers needed."""
        auth_user = self.config.get("api_key")
        auth_passwd = self.config.get("secret_key")

        base64encoded = base64.b64encode(('%s:%s' % (auth_user, auth_passwd)).encode('utf-8')).decode('utf-8').replace('\n', '') 

        headers = {}
        if "user_agent" in self.config:
            headers["User-Agent"] = self.config.get("user_agent")
        headers['Authorization'] = f"Basic {base64encoded}"
        return headers

        
    def get_next_page_token(
        self, response: requests.Response, previous_token: Optional[Any]
    ) -> Optional[Any]:
        """Return a token for identifying next page or None if no more pages."""
       
        parsed = urllib.parse.urlparse(response.url)
        end = urllib.parse.parse_qs(parsed.query).get("end")

        end = cast(datetime, pendulum.parse(end[0]))
        end = end.replace(tzinfo=None) 
        if end > datetime.today():
            return None
        return end.strftime("%Y%m%dT00") , (end + timedelta(self.window)).strftime("%Y%m%dT00")

    def get_url_params(
        self, context: Optional[dict], next_page_token: Optional[Any]
    ) -> Dict[str, Any]:
        """Return a dictionary of values to be used in URL parameterization."""
        params: dict = {}
        if not next_page_token:
            start_date = self.start_date(context)
            start_date = cast(datetime, start_date)
            params["start"] = start_date.strftime("%Y%m%dT00")
            params["end"] = (start_date + timedelta(self.window)).strftime("%Y%m%dT00")

        else:
            start, end = next_page_token
            params["start"] = start
            params["end"] = end
        if self.replication_key:
            params["sort"] = "asc"
            params["order_by"] = self.replication_key

        return params

    def parse_response(self, response: requests.Response) -> Iterable[dict]:
        """Parse the response and return an iterator of result rows."""
        if self.is_no_data_found_error(response):
            yield from []
            return
        zipfile = ZipFile(BytesIO(response.content))
        for file_name in zipfile.namelist():
            with zipfile.open(file_name) as gz_file:
                gz_content = gz_file.read()
                str_content = gzip.decompress(gz_content).decode("utf-8")
                lines = str_content.split("\n")
                for line in lines:
                    if "" == line.strip():
                        continue
                    yield orjson.loads(line)

    def validate_response(self, response: requests.Response) -> None:
        if self.is_no_data_found_error(response):
            self.logger.warning(f"No data found for given request {response.request.url}")
            return
        super().validate_response(response)

        # Amplitude's Export API returns a ZIP body on success. We've seen
        # 200 OK responses with non-ZIP bodies (rate-limit messages, edge
        # error pages, truncated downloads) — feeding those into
        # `ZipFile(...)` raises BadZipFile and crashes the whole sync.
        # Treat them as retriable so singer-sdk's backoff handles them.
        if response.status_code == 200 and not looks_like_zip(response.content):
            content_type = response.headers.get("Content-Type")
            head = response.content[:64]
            raise RetriableAPIError(
                f"Amplitude Export returned 200 but body is not a ZIP "
                f"(Content-Type={content_type!r}, head={head!r})",
                response,
            )

    def is_no_data_found_error(self, response: requests.Response) -> bool:
        return response.status_code == 404 and "Raw data files were not found" in response.text
