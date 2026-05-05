"""Sample-based schema discovery for Amplitude's freeform JSON properties.

Amplitude's `user_properties`, `event_properties`, `global_user_properties`,
`groups`, and `data` fields are arbitrary JSON bags — the platform has no
schema registry on lower-tier plans (the Taxonomy API requires Enterprise).
To capture per-tenant property shapes without hardcoding fields, this module
pulls a recent window of events from the same Export endpoint the sync uses,
unions the observed keys, and infers types from the values seen.

Falls back to `additional_properties=True` if discovery fails so the tap
never silently drops data the customer cares about.
"""

import base64
import gzip
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from io import BytesIO
from typing import Any, Dict, Iterable, Optional, Set, Tuple
from zipfile import ZipFile

import orjson
import requests
from singer_sdk import typing as th

logger = logging.getLogger(__name__)

NESTED_OBJECT_FIELDS = (
    "user_properties",
    "event_properties",
    "global_user_properties",
    "groups",
    "group_properties",
    "data",
    "plan",
)

DEFAULT_WINDOW_HOURS = 24
DEFAULT_MAX_EVENTS = 5000


def _build_export_url(config: Dict[str, Any], start: datetime, end: datetime) -> str:
    base = (
        "https://analytics.eu.amplitude.com/api/2/export"
        if config.get("is_eu_region")
        else "https://amplitude.com/api/2/export"
    )
    return f"{base}?start={start.strftime('%Y%m%dT%H')}&end={end.strftime('%Y%m%dT%H')}"


def _auth_header(config: Dict[str, Any]) -> str:
    creds = f"{config['api_key']}:{config['secret_key']}".encode("utf-8")
    return "Basic " + base64.b64encode(creds).decode("utf-8")


def _iter_sample_events(
    config: Dict[str, Any], window_hours: int, max_events: int
) -> Iterable[Dict[str, Any]]:
    end = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    start = end - timedelta(hours=window_hours)
    url = _build_export_url(config, start, end)
    logger.info(
        "Fetching Amplitude sample for discovery: %s (max %d events)",
        url,
        max_events,
    )
    response = requests.get(url, headers={"Authorization": _auth_header(config)}, timeout=120)
    if response.status_code == 404 and "Raw data files were not found" in response.text:
        logger.warning("Amplitude returned 404 (no data) for discovery window")
        return
    response.raise_for_status()

    yielded = 0
    with ZipFile(BytesIO(response.content)) as zf:
        for name in zf.namelist():
            with zf.open(name) as inner:
                content = gzip.decompress(inner.read()).decode("utf-8")
                for line in content.split("\n"):
                    if not line.strip():
                        continue
                    try:
                        yield orjson.loads(line)
                    except orjson.JSONDecodeError:
                        continue
                    yielded += 1
                    if yielded >= max_events:
                        return


def _infer_type(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "string"


def _resolve_type(key: str, types: Set[str]) -> th.JSONTypeHelper:
    if not types:
        return th.StringType()
    if types == {"boolean"}:
        return th.BooleanType()
    if types == {"integer"}:
        return th.IntegerType()
    if types <= {"integer", "number"}:
        return th.NumberType()
    if types == {"array"}:
        return th.ArrayType(th.AnyType())
    if types == {"object"}:
        return th.ObjectType(additional_properties=True)
    logger.info(
        "Mixed types %s observed for property %s; coercing to string",
        sorted(types),
        key,
    )
    return th.StringType()


def _scan_keys(
    events: Iterable[Dict[str, Any]],
) -> Tuple[Dict[str, Dict[str, Set[str]]], int]:
    field_keys: Dict[str, Dict[str, Set[str]]] = {
        field: defaultdict(set) for field in NESTED_OBJECT_FIELDS
    }
    count = 0
    for event in events:
        count += 1
        for field in NESTED_OBJECT_FIELDS:
            inner = event.get(field)
            if not isinstance(inner, dict):
                continue
            for key, value in inner.items():
                inferred = _infer_type(value)
                if inferred is not None:
                    field_keys[field][key].add(inferred)
    return field_keys, count


def _build_object_schema(keys_by_type: Dict[str, Set[str]]) -> th.ObjectType:
    properties = [
        th.Property(key, _resolve_type(key, types))
        for key, types in sorted(keys_by_type.items())
    ]
    return th.ObjectType(*properties, additional_properties=True)


def discover_nested_schemas(
    config: Dict[str, Any],
) -> Dict[str, th.ObjectType]:
    """Sample recent events and return an ObjectType per nested field.

    Falls back to a permissive (additional_properties=True) ObjectType if the
    sample is empty or the request fails — so unknown properties still flow
    through instead of being silently dropped by Singer SDK validation.
    """

    permissive = {field: th.ObjectType(additional_properties=True) for field in NESTED_OBJECT_FIELDS}

    if not config.get("api_key") or not config.get("secret_key"):
        logger.warning("Amplitude credentials missing; using permissive schemas")
        return permissive

    window_hours = int(config.get("discovery_window_hours") or DEFAULT_WINDOW_HOURS)
    max_events = int(config.get("discovery_max_events") or DEFAULT_MAX_EVENTS)

    try:
        events = _iter_sample_events(config, window_hours, max_events)
        field_keys, scanned = _scan_keys(events)
    except requests.RequestException as exc:
        logger.warning("Amplitude discovery sample failed: %s; using permissive schemas", exc)
        return permissive
    except Exception as exc:
        logger.warning("Amplitude discovery raised %s; using permissive schemas", exc)
        return permissive

    if scanned == 0:
        logger.warning("Amplitude discovery sample returned 0 events; using permissive schemas")
        return permissive

    schemas: Dict[str, th.ObjectType] = {}
    for field in NESTED_OBJECT_FIELDS:
        keys = field_keys[field]
        if not keys:
            schemas[field] = th.ObjectType(additional_properties=True)
        else:
            schemas[field] = _build_object_schema(keys)
            logger.info(
                "Discovered %d %s key(s) from %d event sample",
                len(keys),
                field,
                scanned,
            )

    return schemas
