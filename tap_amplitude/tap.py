"""Amplitude tap class."""

from typing import List

from singer_sdk import Stream, Tap
from singer_sdk import typing as th

from tap_amplitude.streams import EventStream

STREAM_TYPES = [EventStream]


class TapAmplitude(Tap):
    """Amplitude tap class."""

    name = "tap-amplitude"

    config_jsonschema = th.PropertiesList(
        th.Property(
            "api_key",
            th.StringType,
            required=True,
            description="Amplitude project API key",
        ),
        th.Property(
            "secret_key",
            th.StringType,
            required=True,
            description="Amplitude project secret key",
        ),
        th.Property(
            "start_date",
            th.DateTimeType,
            description="The earliest record date to sync",
        ),
        th.Property(
            "window_days",
            th.IntegerType,
            default=5,
            description="Window of days fetched per Export API request",
        ),
        th.Property(
            "is_eu_region",
            th.BooleanType,
            default=False,
            description="Set to true for EU-region Amplitude projects",
        ),
        th.Property(
            "discovery_window_hours",
            th.IntegerType,
            default=24,
            description=(
                "Hours of recent events to sample during discovery to infer "
                "user_properties / event_properties shape"
            ),
        ),
        th.Property(
            "discovery_max_events",
            th.IntegerType,
            default=5000,
            description="Maximum events to scan during discovery",
        ),
    ).to_dict()

    def discover_streams(self) -> List[Stream]:
        return [stream_class(tap=self) for stream_class in STREAM_TYPES]


if __name__ == "__main__":
    TapAmplitude.cli()