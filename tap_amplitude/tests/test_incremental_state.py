"""Tests for incremental-state resumption in AmplitudeStream.start_date."""

import pendulum

from tap_amplitude.tap import TapAmplitude


CONFIG = {
    "api_key": "x",
    "secret_key": "y",
    "start_date": "2026-01-01T06:00:00Z",
}


def _events_stream(state: dict):
    tap = TapAmplitude(config=CONFIG, state=state, parse_env_config=False)
    return next(s for s in tap.streams.values() if s.name == "events")


def test_falls_back_to_config_start_date_when_state_is_empty():
    stream = _events_stream(state={})
    assert stream.start_date() == pendulum.parse("2026-01-01T06:00:00Z")


def test_uses_finalized_bookmark_when_present():
    state = {
        "bookmarks": {
            "events": {
                "replication_key": "server_upload_time",
                "replication_key_value": "2026-05-30 13:59:59.897000",
            }
        }
    }
    stream = _events_stream(state=state)
    assert stream.start_date() == pendulum.parse("2026-05-30 13:59:59.897000")


def test_resumes_from_progress_markers_after_interrupted_run():
    # Mirrors the real failure mode: prior sync crashed mid-flight, so the
    # bookmark was never promoted out of progress_markers. We must NOT fall
    # back to config.start_date here — that re-syncs everything.
    state = {
        "bookmarks": {
            "events": {
                "starting_replication_value": "2026-01-01T06:00:00Z",
                "progress_markers": {
                    "Note": "Progress is not resumable if interrupted.",
                    "replication_key": "server_upload_time",
                    "replication_key_value": "2026-05-27 21:59:59.984000",
                },
            }
        }
    }
    stream = _events_stream(state=state)
    assert stream.start_date() == pendulum.parse("2026-05-27 21:59:59.984000")


def test_ignores_progress_markers_for_mismatched_replication_key():
    state = {
        "bookmarks": {
            "events": {
                "progress_markers": {
                    "replication_key": "event_time",
                    "replication_key_value": "2026-05-27 21:59:59.984000",
                }
            }
        }
    }
    stream = _events_stream(state=state)
    assert stream.start_date() == pendulum.parse("2026-01-01T06:00:00Z")
