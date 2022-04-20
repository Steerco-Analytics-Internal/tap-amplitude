"""Stream type classes for tap-amplitude."""

from pathlib import Path
from typing import Any, Dict, Optional, Union, List, Iterable

from singer_sdk import typing as th  # JSON Schema typing helpers

from tap_amplitude.client import AmplitudeStream

# TODO: Delete this is if not using json files for schema definition
SCHEMAS_DIR = Path(__file__).parent / Path("./schemas")
# TODO: - Override `UsersStream` and `GroupsStream` with your own stream definition.
#       - Copy-paste as many times as needed to create multiple stream types.


class UsersStream(AmplitudeStream):
    """Define custom stream."""
    name = "users"
    path = "/users"
    primary_keys = ["id"]
    replication_key = None
    # Optionally, you may also use `schema_filepath` in place of `schema`:
    # schema_filepath = SCHEMAS_DIR / "users.json"
    schema = th.PropertiesList(
        th.Property("name", th.StringType),
        th.Property(
            "id",
            th.StringType,
            description="The user's system ID"
        ),
        th.Property(
            "age",
            th.IntegerType,
            description="The user's age in years"
        ),
        th.Property(
            "email",
            th.StringType,
            description="The user's email address"
        ),
        th.Property("street", th.StringType),
        th.Property("city", th.StringType),
        th.Property(
            "state",
            th.StringType,
            description="State name in ISO 3166-2 format"
        ),
        th.Property("zip", th.StringType),
    ).to_dict()


class GroupsStream(AmplitudeStream):
    """Define custom stream."""
    name = "groups"
    path = "/groups"
    primary_keys = ["id"]
    replication_key = "modified"
    schema = th.PropertiesList(
        th.Property("name", th.StringType),
        th.Property("id", th.StringType),
        th.Property("modified", th.DateTimeType),
    ).to_dict()


class EventStream(AmplitudeStream):

    name = "events"
    path = ""
    primary_keys = ["event_id"]

    schema = th.PropertiesList(
        th.Property('app', th.IntegerType),
        th.Property('device_id', th.StringType),
        th.Property('user_id', th.CustomType({"type": ["string", "integer"]})),
        th.Property('client_event_time', th.StringType),
        th.Property('event_id', th.IntegerType),
        th.Property('session_id', th.IntegerType),
        th.Property('event_type', th.StringType),
        th.Property('amplitude_event_type', th.CustomType({"type": ["string", "integer"]})),
        th.Property('version_name', th.CustomType({"type": ["string", "integer"]})),
        th.Property('platform', th.StringType),
        th.Property('os_name', th.StringType),
        th.Property('os_version', th.StringType),
        th.Property('device_brand', th.CustomType({"type": ["string", "integer"]})),
        th.Property('device_manufacturer', th.CustomType({"type": ["string", "integer"]})),
        th.Property('device_model', th.StringType),
        th.Property('device_family', th.StringType),
        th.Property('device_type', th.StringType),
        th.Property('device_carrier', th.CustomType({"type": ["string", "integer"]})),
        th.Property('location_lat', th.CustomType({"type": ["string", "integer"]})),
        th.Property('location_lng', th.CustomType({"type": ["string", "integer"]})),
        th.Property('ip_address', th.StringType),
        th.Property('country', th.StringType),
        th.Property('language', th.StringType),
        th.Property('library', th.StringType),
        th.Property('city', th.StringType),
        th.Property('region', th.StringType),
        th.Property('dma', th.CustomType({"type": ["string", "integer"]})),
        th.Property('event_properties', th.ObjectType(      
            th.Property('sessionURL', th.StringType),
        )),
        th.Property('user_properties', th.CustomType({"type": ["object"]})),
        th.Property('global_user_properties', th.CustomType({"type": ["object"]})),
        th.Property('group_properties', th.CustomType({"type": ["object"]})),
        th.Property('event_time', th.DateTimeType),
        th.Property('client_upload_time', th.DateTimeType),
        th.Property('server_upload_time', th.DateTimeType),
        th.Property('server_received_time', th.DateTimeType),
        th.Property('amplitude_id', th.IntegerType),
        th.Property('idfa', th.CustomType({"type": ["string", "integer"]})),
        th.Property('adid', th.CustomType({"type": ["string", "integer"]})),
        th.Property('data', th.CustomType({"type": ["custom"]})),
        th.Property('paying', th.CustomType({"type": ["string", "integer"]})),
        th.Property('start_version', th.CustomType({"type": ["string", "integer"]})),
        th.Property('user_creation_time', th.DateTimeType),
        th.Property('uuid', th.StringType),
        th.Property('groups', th.CustomType({"type": ["custom"]})),
        th.Property('sample_rate', th.CustomType({"type": ["string", "integer"]})),
        th.Property('$insert_id', th.StringType),
        th.Property('$insert_key', th.StringType),
        th.Property('is_attribution_event', th.BooleanType),
        th.Property('amplitude_attribution_ids', th.CustomType({"type": ["string", "integer"]})),
        th.Property('plan', th.CustomType({"type": ["custom"]})),
        th.Property('partner_id', th.CustomType({"type": ["string", "integer"]})),
        th.Property('$schema', th.IntegerType),
        th.Property('processed_time', th.DateTimeType),
).to_dict()