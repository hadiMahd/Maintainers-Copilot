"""Unit tests for error display component."""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "streamlit_app"))

from streamlit_app.components.errors import ERROR_DISPLAY_MAP, display_error
from streamlit_app.models import UIErrorMessage


def test_display_error_none_does_nothing():
    with patch("streamlit_app.components.errors.st") as mock_st:
        display_error(None)
        mock_st.error.assert_not_called()
        mock_st.warning.assert_not_called()


def test_display_auth_error():
    with patch("streamlit_app.components.errors.st") as mock_st:
        err = UIErrorMessage(code="authentication_required", message="Please log in")
        display_error(err)
        mock_st.error.assert_called_once()


def test_display_validation_error():
    with patch("streamlit_app.components.errors.st") as mock_st:
        err = UIErrorMessage(code="validation_error", message="Invalid input")
        display_error(err)
        mock_st.warning.assert_called_once()


def test_display_timeout_error_shows_retry_hint():
    with patch("streamlit_app.components.errors.st") as mock_st:
        err = UIErrorMessage(code="backend_timeout", message="Timed out")
        display_error(err)
        call_args = mock_st.warning.call_args[0]
        assert "try again" in str(call_args[0]).lower()


def test_error_display_map_coverage():
    expected_codes = [
        "authentication_required",
        "access_denied",
        "validation_error",
        "request_too_large",
        "backend_timeout",
        "backend_unavailable",
        "backend_error",
    ]
    for code in expected_codes:
        assert code in ERROR_DISPLAY_MAP, f"Missing display mapping for {code}"
