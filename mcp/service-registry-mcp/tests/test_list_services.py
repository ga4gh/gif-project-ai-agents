import ga4gh_registry as reg
from helpers import ENVELOPE_FIELDS, call, fake_fetch, fetch_fail, fetch_ok, http_status_error

TRS_SERVICE = {
    "id": "org.ga4gh.dockstore",
    "name": "Dockstore",
    "type": {"group": "org.ga4gh", "artifact": "trs", "version": "2.0.0"},
    "organization": {"name": "Dockstore Team", "url": "https://dockstore.org"},
    "url": "https://dockstore.org/api/ga4gh/trs/v2",
}
WES_SERVICE = {
    "id": "org.ga4gh.wes-example",
    "name": "WES Example",
    "type": {"group": "org.ga4gh", "artifact": "wes", "version": "1.0.0"},
    "organization": {"name": "Example Org", "url": "https://example.org"},
    "url": "https://example.org/wes",
}


async def test_allow_returns_all_services_without_filter(monkeypatch):
    monkeypatch.setattr(reg, "_fetch", fake_fetch(fetch_ok([TRS_SERVICE, WES_SERVICE])))

    envelope = await call(reg.list_services)

    assert envelope["policy"]["decision"] == "allow"
    assert envelope["data"]["count"] == 2
    assert envelope["errors"] == []
    assert envelope["source"]["endpoint"] == "https://registry.ga4gh.org/v1/services"


async def test_allow_filters_by_service_type(monkeypatch):
    monkeypatch.setattr(reg, "_fetch", fake_fetch(fetch_ok([TRS_SERVICE, WES_SERVICE])))

    envelope = await call(reg.list_services, service_type="trs")

    assert envelope["data"]["count"] == 1
    assert envelope["data"]["services"][0]["id"] == "org.ga4gh.dockstore"


async def test_allow_returns_empty_list_when_filter_matches_nothing(monkeypatch):
    monkeypatch.setattr(reg, "_fetch", fake_fetch(fetch_ok([TRS_SERVICE])))

    envelope = await call(reg.list_services, service_type="tes")

    assert envelope["policy"]["decision"] == "allow"
    assert envelope["data"] == {"services": [], "count": 0}


async def test_deny_on_upstream_error(monkeypatch):
    error = http_status_error(503)
    monkeypatch.setattr(reg, "_fetch", fake_fetch(fetch_fail(error)))

    envelope = await call(reg.list_services)

    assert envelope["policy"]["decision"] == "deny"
    assert envelope["data"] is None
    assert envelope["errors"][0] == {
        "type": "UpstreamError",
        "code": "HTTP_503",
        "message": str(error),
        "retryable": True,
    }


async def test_registry_url_override_is_reflected_in_source_and_query(monkeypatch):
    monkeypatch.setattr(reg, "_fetch", fake_fetch(fetch_ok([TRS_SERVICE])))

    envelope = await call(reg.list_services, registry_url="https://custom.example.org/v1")

    assert envelope["source"]["endpoint"] == "https://custom.example.org/v1/services"
    assert envelope["provenance"]["query_provenance"]["registry_url"] == "https://custom.example.org/v1"


async def test_envelope_has_exactly_seven_top_level_fields(monkeypatch):
    monkeypatch.setattr(reg, "_fetch", fake_fetch(fetch_ok([TRS_SERVICE])))

    envelope = await call(reg.list_services)

    assert set(envelope.keys()) == ENVELOPE_FIELDS
