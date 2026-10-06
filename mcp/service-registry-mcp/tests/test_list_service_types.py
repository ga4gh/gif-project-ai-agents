import ga4gh_registry as reg
from helpers import ENVELOPE_FIELDS, call, fake_fetch, fetch_fail, fetch_ok, http_status_error

TYPES = [
    {"group": "org.ga4gh", "artifact": "trs", "version": "2.0.0"},
    {"group": "org.ga4gh", "artifact": "drs", "version": "1.4.0"},
]


async def test_allow_returns_types_and_count(monkeypatch):
    monkeypatch.setattr(reg, "_fetch", fake_fetch(fetch_ok(TYPES)))

    envelope = await call(reg.list_service_types)

    assert envelope["policy"]["decision"] == "allow"
    assert envelope["data"]["count"] == 2
    assert envelope["data"]["types"] == TYPES
    assert envelope["source"]["endpoint"] == "https://registry.ga4gh.org/v1/services/types"


async def test_deny_on_upstream_error(monkeypatch):
    error = http_status_error(500)
    monkeypatch.setattr(reg, "_fetch", fake_fetch(fetch_fail(error)))

    envelope = await call(reg.list_service_types)

    assert envelope["policy"]["decision"] == "deny"
    assert envelope["errors"][0]["code"] == "HTTP_500"
    assert envelope["errors"][0]["retryable"] is True


async def test_non_list_payload_becomes_empty_list(monkeypatch):
    """Documents current (minimal) behavior: an unexpected payload shape is
    tolerated as an empty result, not a denied contract violation."""
    monkeypatch.setattr(reg, "_fetch", fake_fetch(fetch_ok({"unexpected": "shape"})))

    envelope = await call(reg.list_service_types)

    assert envelope["policy"]["decision"] == "allow"
    assert envelope["data"] == {"types": [], "count": 0}


async def test_allow_with_no_types_registered(monkeypatch):
    monkeypatch.setattr(reg, "_fetch", fake_fetch(fetch_ok([])))

    envelope = await call(reg.list_service_types)

    assert envelope["policy"]["decision"] == "allow"
    assert envelope["data"] == {"types": [], "count": 0}


async def test_registry_url_override_is_reflected_in_source_and_query(monkeypatch):
    monkeypatch.setattr(reg, "_fetch", fake_fetch(fetch_ok(TYPES)))

    envelope = await call(reg.list_service_types, registry_url="https://custom.example.org/v1")

    assert envelope["source"]["endpoint"] == "https://custom.example.org/v1/services/types"
    assert envelope["provenance"]["query_provenance"]["registry_url"] == "https://custom.example.org/v1"


async def test_envelope_has_exactly_seven_top_level_fields(monkeypatch):
    monkeypatch.setattr(reg, "_fetch", fake_fetch(fetch_ok(TYPES)))

    envelope = await call(reg.list_service_types)

    assert set(envelope.keys()) == ENVELOPE_FIELDS
