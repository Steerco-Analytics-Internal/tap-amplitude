"""Stream type classes for tap-amplitude."""

from singer_sdk import typing as th  # JSON Schema typing helpers

from tap_amplitude.client import AmplitudeStream
from tap_amplitude.discovery import NESTED_OBJECT_FIELDS, discover_nested_schemas


_STATIC_PROPERTIES = [
    th.Property("app", th.IntegerType),
    th.Property("device_id", th.StringType),
    th.Property("user_id", th.StringType),
    th.Property("client_event_time", th.StringType),
    th.Property("event_id", th.IntegerType),
    th.Property("session_id", th.IntegerType),
    th.Property("event_type", th.StringType),
    th.Property("amplitude_event_type", th.StringType),
    th.Property("version_name", th.StringType),
    th.Property("platform", th.StringType),
    th.Property("os_name", th.StringType),
    th.Property("os_version", th.StringType),
    th.Property("device_brand", th.StringType),
    th.Property("device_manufacturer", th.StringType),
    th.Property("device_model", th.StringType),
    th.Property("device_family", th.StringType),
    th.Property("device_type", th.StringType),
    th.Property("device_carrier", th.StringType),
    th.Property("location_lat", th.StringType),
    th.Property("location_lng", th.StringType),
    th.Property("ip_address", th.StringType),
    th.Property("country", th.StringType),
    th.Property("language", th.StringType),
    th.Property("library", th.StringType),
    th.Property("city", th.StringType),
    th.Property("region", th.StringType),
    th.Property("dma", th.StringType),
    th.Property("event_time", th.DateTimeType),
    th.Property("client_upload_time", th.DateTimeType),
    th.Property("server_upload_time", th.DateTimeType),
    th.Property("server_received_time", th.DateTimeType),
    th.Property("amplitude_id", th.IntegerType),
    th.Property("idfa", th.StringType),
    th.Property("adid", th.StringType),
    th.Property("paying", th.StringType),
    th.Property("start_version", th.StringType),
    th.Property("user_creation_time", th.DateTimeType),
    th.Property("uuid", th.StringType),
    th.Property("sample_rate", th.StringType),
    th.Property("$insert_id", th.StringType),
    th.Property("$insert_key", th.StringType),
    th.Property("is_attribution_event", th.BooleanType),
    th.Property("amplitude_attribution_ids", th.StringType),
    th.Property("partner_id", th.StringType),
    th.Property("$schema", th.IntegerType),
    th.Property("processed_time", th.DateTimeType),
]


def _build_event_schema(config: dict) -> dict:
    nested = discover_nested_schemas(config)
    properties = list(_STATIC_PROPERTIES)
    for field in NESTED_OBJECT_FIELDS:
        properties.append(th.Property(field, nested[field]))
    return th.PropertiesList(*properties).to_dict()


class EventStream(AmplitudeStream):

    name = "events"
    path = "export"
    primary_keys = ["event_id"]
    replication_key = "server_upload_time"

    def __init__(self, tap, schema=None, name=None):
        super().__init__(
            tap=tap,
            schema=schema or _build_event_schema(tap.config),
            name=name,
        )
