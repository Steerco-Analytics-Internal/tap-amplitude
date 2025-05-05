"""Stream type classes for tap-amplitude."""

from singer_sdk import typing as th  # JSON Schema typing helpers

from tap_amplitude.client import AmplitudeStream


class EventStream(AmplitudeStream):

    name = "events"
    path = "export"
    primary_keys = ["event_id"]
    replication_key = "server_upload_time"
    
    schema = th.PropertiesList(
        th.Property('app', th.IntegerType),
        th.Property('device_id', th.StringType),
        th.Property('user_id', th.StringType),
        th.Property('client_event_time', th.StringType),
        th.Property('event_id', th.IntegerType),
        th.Property('session_id', th.IntegerType),
        th.Property('event_type', th.StringType),
        th.Property('amplitude_event_type', th.StringType),
        th.Property('version_name',th.StringType),
        th.Property('platform', th.StringType),
        th.Property('os_name', th.StringType),
        th.Property('os_version', th.StringType),
        th.Property('device_brand', th.StringType),
        th.Property('device_manufacturer', th.StringType),
        th.Property('device_model', th.StringType),
        th.Property('device_family', th.StringType),
        th.Property('device_type', th.StringType),
        th.Property('device_carrier', th.StringType),
        th.Property('location_lat', th.StringType),
        th.Property('location_lng', th.StringType),
        th.Property('ip_address', th.StringType),
        th.Property('country', th.StringType),
        th.Property('language', th.StringType),
        th.Property('library', th.StringType),
        th.Property('city', th.StringType),
        th.Property('region', th.StringType),
        th.Property('dma', th.StringType),
        th.Property('event_properties', th.ObjectType(      
            th.Property('sessionURL', th.StringType),
        )),
        th.Property('user_properties',th.ObjectType()),
        th.Property('global_user_properties',th.ObjectType()),
        th.Property('group_properties',th.ObjectType()),
        th.Property('event_time', th.DateTimeType),
        th.Property('client_upload_time', th.DateTimeType),
        th.Property('server_upload_time', th.DateTimeType),
        th.Property('server_received_time', th.DateTimeType),
        th.Property('amplitude_id', th.IntegerType),
        th.Property('idfa', th.StringType),
        th.Property('adid', th.StringType),
        th.Property('data', th.ObjectType()),
        th.Property('paying', th.StringType),
        th.Property('start_version', th.StringType),
        th.Property('user_creation_time', th.DateTimeType),
        th.Property('uuid', th.StringType),
        th.Property('groups', th.ObjectType()),
        th.Property('sample_rate', th.StringType),
        th.Property('$insert_id', th.StringType),
        th.Property('$insert_key', th.StringType),
        th.Property('is_attribution_event', th.BooleanType),
        th.Property('amplitude_attribution_ids', th.StringType),
        th.Property('plan', th.ObjectType()),
        th.Property('partner_id', th.StringType),
        th.Property('$schema', th.IntegerType),
        th.Property('processed_time', th.DateTimeType),
).to_dict()