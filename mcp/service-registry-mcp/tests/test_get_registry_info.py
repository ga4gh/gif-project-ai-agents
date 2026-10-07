import ga4gh_registry as reg
from helpers import ENVELOPE_FIELDS, call, fake_fetch, fetch_fail, fetch_ok, http_status_error

REGISTRY_INFO = {
    "id": "org.ga4gh.registry",
    "name": "GA4GH Standards and Implementations Registry",
    "type": {"group": "org.ga4gh", "artifact": "service-registry", "version": "1.0.0"},
    "organization": {"name": "Global Alliance for Genomics and Health", "url": "https://ga4gh.org"},
    "version": "1.0.0",
    "url": "https://registry.ga4gh.org/v1",
}


async def test_allow_returns_registry_info(monkeypatch):
    monkeypatch.setattr(reg, "_fetch", fake_fetch(fetch_ok(REGISTRY_INFO)))

    envelope = await call(reg.get_registry_info)

    assert envelope["policy"]["decision"] == "allow"
    assert envelope["data"] == REGISTRY_INFO
    assert envelope["benchmark"] is None
    assert envelope["source"]["endpoint"] == "https://registry.ga4gh.org/v1/service-info"


async def test_deny_on_upstream_error(monkeypatch):
    error = http_status_error(500)
    monkeypatch.setattr(reg, "_fetch", fake_fetch(fetch_fail(error)))

    envelope = await call(reg.get_registry_info)

    assert envelope["policy"]["decision"] == "deny"
    assert envelope["benchmark"] is None
    assert envelope["errors"][0]["code"] == "HTTP_500"
    assert envelope["errors"][0]["retryable"] is True


async def test_deny_not_found(monkeypatch):
    error = http_status_error(404)
    monkeypatch.setattr(reg, "_fetch", fake_fetch(fetch_fail(error)))

    envelope = await call(reg.get_registry_info)

    assert envelope["policy"]["decision"] == "deny"
    assert envelope["errors"][0]["code"] == "HTTP_404"
    assert envelope["errors"][0]["retryable"] is False
    assert envelope["data"] is None


async def test_registry_url_override_is_reflected_in_source_and_query(monkeypatch):
    monkeypatch.setattr(reg, "_fetch", fake_fetch(fetch_ok(REGISTRY_INFO)))

    envelope = await call(reg.get_registry_info, registry_url="https://custom.example.org/v1")

    assert envelope["source"]["endpoint"] == "https://custom.example.org/v1/service-info"
    assert envelope["provenance"]["query_provenance"]["registry_url"] == "https://custom.example.org/v1"


async def test_envelope_has_exactly_seven_top_level_fields(monkeypatch):
    monkeypatch.setattr(reg, "_fetch", fake_fetch(fetch_ok(REGISTRY_INFO)))

    envelope = await call(reg.get_registry_info)

    assert set(envelope.keys()) == ENVELOPE_FIELDS
