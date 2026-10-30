import ga4gh_registry as reg
from helpers import ENVELOPE_FIELDS, call, connect_error, fake_fetch, fetch_fail, fetch_ok, http_status_error

SERVICE = {
    "id": "org.ga4gh.dockstore",
    "name": "Dockstore",
    "type": {"group": "org.ga4gh", "artifact": "trs", "version": "2.0.0"},
    "organization": {"name": "Dockstore Team", "url": "https://dockstore.org"},
    "version": "1.15.0",
    "url": "https://dockstore.org/api/ga4gh/trs/v2",
}


async def test_allow_returns_full_service_payload(monkeypatch):
    monkeypatch.setattr(reg, "_fetch", fake_fetch(fetch_ok(SERVICE)))

    envelope = await call(reg.get_service, service_id="org.ga4gh.dockstore")

    assert envelope["policy"]["decision"] == "allow"
    assert envelope["data"] == SERVICE
    assert envelope["source"]["endpoint"] == "https://registry.ga4gh.org/v1/services/org.ga4gh.dockstore"


async def test_deny_not_found(monkeypatch):
    error = http_status_error(404)
    monkeypatch.setattr(reg, "_fetch", fake_fetch(fetch_fail(error)))

    envelope = await call(reg.get_service, service_id="does-not-exist")

    assert envelope["policy"]["decision"] == "deny"
    assert envelope["policy"]["reason"]["code"] == "HTTP_404"
    assert envelope["errors"][0]["retryable"] is False
    assert envelope["data"] is None


async def test_deny_connection_error_is_retryable(monkeypatch):
    error = connect_error()
    monkeypatch.setattr(reg, "_fetch", fake_fetch(fetch_fail(error)))

    envelope = await call(reg.get_service, service_id="org.ga4gh.dockstore")

    assert envelope["errors"][0]["code"] == "REQUEST_FAILED"
    assert envelope["errors"][0]["retryable"] is True


async def test_envelope_has_exactly_seven_top_level_fields(monkeypatch):
    monkeypatch.setattr(reg, "_fetch", fake_fetch(fetch_ok(SERVICE)))

    envelope = await call(reg.get_service, service_id="org.ga4gh.dockstore")

    assert set(envelope.keys()) == ENVELOPE_FIELDS
