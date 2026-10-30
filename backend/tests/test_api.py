import copy
import pytest
from unittest.mock import patch
from django.test import Client
from django.urls import reverse


@pytest.mark.django_db
def test_no_release_json_503():
    c = Client()
    for route in [
        "/api/v1/stories/",
        "/api/v1/stories/aza-zaraina/",
        "/api/v1/questions/",
        "/api/v1/resources/",
        "/api/v1/content-version/",
    ]:
        res = c.get(route)
        assert res.status_code == 503
        assert res["Content-Type"].startswith("application/json")
        assert res.json() == {
            "error": {
                "code": "CONTENT_NOT_PUBLISHED",
                "message": "Contenu public indisponible",
            }
        }
        assert not res.cookies


@pytest.mark.django_db
def test_unknown_slug_404_in_release():
    with patch(
        "apps.content_api.views.active_release", return_value=(None, {"files": []})
    ):
        r = Client().get("/api/v1/stories/unknown/")
        assert r.status_code == 404


@pytest.mark.django_db
def test_no_write_methods():
    c = Client()
    for path in [
        "/api/v1/stories/",
        "/api/v1/resources/",
        "/api/v1/questions/",
        "/api/v1/content-version/",
    ]:
        for method in [c.post, c.put, c.patch, c.delete]:
            r = method(path, content_type="application/json")
            assert r.status_code == 405
            assert r.json()["error"]["code"] == "METHOD_NOT_ALLOWED"


@pytest.mark.django_db
def test_nonexistent_route_is_json():
    res = Client().get("/api/v1/players/")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.django_db
def test_example_snapshot_story_and_etag():
    payload = {
        "id": "aza-zaraina",
        "number": "01",
        "title": {"fr": "A", "mg": "B"},
        "nodes": {
            "start": {
                "kind": "ending",
                "title": {"fr": "F", "mg": "F"},
                "text": {"fr": "T", "mg": "T"},
            }
        },
    }
    manifest = {"assets": {}, "files": []}
    with patch(
        "apps.content_api.views.active_release",
        return_value=(None, {"files": [{"path": "stories/aza-zaraina.json"}]}),
    ), patch(
        "apps.content_api.views.read_content",
        return_value=(copy.deepcopy(payload), manifest),
    ):
        c = Client()
        res = c.get("/api/v1/stories/aza-zaraina/")
        assert res.status_code == 200
        assert res.json() == payload
        assert "ETag" in res
        cached = c.get("/api/v1/stories/aza-zaraina/", HTTP_IF_NONE_MATCH=res["ETag"])
        assert cached.status_code == 304
        assert cached.content == b""


@pytest.mark.django_db
def test_swagger_schema_json(admin_client, settings):
    settings.SWAGGER_PASSWORD = "strong-documentation-password-123"
    from django.core.signing import TimestampSigner
    admin_client.cookies["safidiko_swagger_access"] = TimestampSigner(salt="safidiko.swagger.access.v1").sign("swagger-granted-v1")
    r = admin_client.get("/api/swagger.json")
    assert r.status_code == 200
    body = r.json()
    from swagger_spec_validator.validator20 import validate_spec

    validate_spec(body)
    assert "paths" in body
    assert "/v1/stories/" in body["paths"]


@pytest.mark.django_db
def test_head_options_no_cookie():
    c = Client()
    for method in [c.head, c.options]:
        r = method("/api/v1/stories/")
        assert not r.cookies
        assert r.status_code in (200, 503)
