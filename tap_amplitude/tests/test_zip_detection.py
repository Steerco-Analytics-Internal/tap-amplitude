"""Unit tests for the ZIP magic-byte guard used by the Export API streams."""

from tap_amplitude.client import ZIP_MAGIC, looks_like_zip


def test_real_zip_bytes_pass():
    assert looks_like_zip(b"PK\x03\x04" + b"\x00" * 30) is True


def test_html_error_page_fails():
    assert looks_like_zip(b"<html><body>Service unavailable</body></html>") is False


def test_json_rate_limit_body_fails():
    assert looks_like_zip(b'{"error":"too many requests"}') is False


def test_empty_body_fails():
    assert looks_like_zip(b"") is False


def test_truncated_zip_header_fails():
    # Only the first two magic bytes — should not be mistaken for a full zip
    assert looks_like_zip(b"PK") is False


def test_magic_constant_matches_local_file_header():
    # If this constant ever drifts the guard would let bad bodies through,
    # so pin it explicitly.
    assert ZIP_MAGIC == b"PK\x03\x04"
