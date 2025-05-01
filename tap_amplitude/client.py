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
        if self.replication_key:
            bookmarked_replication_key_value = self.get_starting_replication_key_value(context)
            if bookmarked_replication_key_value:
                bookmarked_replication_key_value = pendulum.parse(bookmarked_replication_key_value)
                return bookmarked_replication_key_value
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


    def is_no_data_found_error(self, response: requests.Response) -> bool:
        return response.status_code == 404 and "Raw data files were not found" in response.text
