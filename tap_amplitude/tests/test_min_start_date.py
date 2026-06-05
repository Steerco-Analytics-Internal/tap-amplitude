"""Tests for the min_start_date floor on AmplitudeStream.start_date."""

import pendulum

from tap_amplitude.tap import TapAmplitude


BASE_CONFIG = {
    "api_key": "x",
    "secret_key": "y",
    "start_date": "2026-01-01T06:00:00Z",
}


def _events_stream(config_overrides: dict, state: dict):
    config = {**BASE_CONFIG, **config_overrides}
    tap = TapAmplitude(config=config, state=state, parse_env_config=False)
    return next(s for s in tap.streams.values() if s.name == "events")


def test_floor_clamps_old_config_start_date_to_min_start_date():
    # Reproduces the hotglue override_start_date failure mode: runtime
    # rewrote start_date to Jan 1 and wiped state, but min_start_date
    # survives untouched and floors the effective start.
    stream = _events_stream(
        config_overrides={"min_start_date": "2026-03-01T06:00:00Z"},
        state={},
    )
    assert stream.start_date() == pendulum.parse("2026-03-01T06:00:00Z")


def test_floor_inactive_when_resolved_start_is_newer():
    stream = _events_stream(
        config_overrides={
            "start_date": "2026-05-15T00:00:00Z",
            "min_start_date": "2026-03-01T06:00:00Z",
        },
        state={},
    )
    assert stream.start_date() == pendulum.parse("2026-05-15T00:00:00Z")


def test_state_bookmark_wins_over_floor_when_newer():
    state = {
        "bookmarks": {
            "events": {
                "replication_key": "server_upload_time",
                "replication_key_value": "2026-05-30 13:59:59.897000",
            }
        }
    }
    stream = _events_stream(
        config_overrides={"min_start_date": "2026-03-01T06:00:00Z"},
        state=state,
    )
    assert stream.start_date() == pendulum.parse("2026-05-30 13:59:59.897000")


def test_floor_clamps_stale_state_bookmark_forward():
    # If state somehow holds an older bookmark than min_start_date, the
    # floor still applies — guards against bad state from prior bad runs.
    state = {
        "bookmarks": {
            "events": {
                "replication_key": "server_upload_time",
                "replication_key_value": "2026-01-15T00:00:00Z",
            }
        }
    }
    stream = _events_stream(
        config_overrides={"min_start_date": "2026-03-01T06:00:00Z"},
        state=state,
    )
    assert stream.start_date() == pendulum.parse("2026-03-01T06:00:00Z")


def test_no_floor_when_min_start_date_unset():
    # Behavior must be identical to v1.0.3 when min_start_date is not set.
    stream = _events_stream(config_overrides={}, state={})
    assert stream.start_date() == pendulum.parse("2026-01-01T06:00:00Z")
