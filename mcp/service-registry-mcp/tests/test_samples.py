"""Guards issues #4 and #5 directly against the committed sample files,
rather than only against inline mocked data in the other test modules.
"""

import json
from pathlib import Path

from helpers import ENVELOPE_FIELDS

SAMPLES_DIR = Path(__file__).parent.parent / "samples"


def test_sample_request_is_a_valid_tool_call():
    request = json.loads((SAMPLES_DIR / "list_services_request.json").read_text())

    assert request["tool"] == "list_services"
    assert "arguments" in request


def test_sample_response_has_exactly_seven_top_level_fields():
    response = json.loads((SAMPLES_DIR / "list_services_response.json").read_text())

    assert set(response.keys()) == ENVELOPE_FIELDS
    assert response["policy"]["decision"] == "allow"
