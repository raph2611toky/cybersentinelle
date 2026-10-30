"""Tests d'intégration Swagger indépendamment de Django admin."""
import pytest
from django.core.signing import TimestampSigner
from django.test import Client


@pytest.mark.django_db
def test_docs_never_redirect_to_django_admin(settings):
    settings.SWAGGER_ENABLED = True
    settings.SWAGGER_PASSWORD = "swagger-testing-password-123456"
    c = Client()
    r = c.get("/api/docs/")
    assert r.status_code == 302
    assert r["Location"].startswith("/api/swagger/login/")
    assert "/admin/" not in r["Location"]
    assert c.get("/api/swagger.json").status_code == 401
    assert c.get("/api/swagger.json").json()["error"]["code"] == "SWAGGER_AUTH_REQUIRED"


@pytest.mark.django_db
def test_swagger_password_cookie_and_logout(settings):
    settings.SWAGGER_PASSWORD = "swagger-testing-password-123456"
    c = Client(enforce_csrf_checks=True)
    login = c.get("/api/swagger/login/?next=/api/docs/")
    assert login.status_code == 200
    csrf = c.cookies["csrftoken"].value
    assert c.post("/api/swagger/unlock/", data='{"password":"bad"}', content_type="application/json", HTTP_X_CSRFTOKEN=csrf).status_code == 401
    r = c.post("/api/swagger/unlock/", data='{"password":"swagger-testing-password-123456","next":"/api/docs/"}', content_type="application/json", HTTP_X_CSRFTOKEN=csrf)
    assert r.status_code == 200, r.content
    assert r.json()["redirect"] == "/api/docs/"
    assert c.get("/api/docs/").status_code == 200
    assert c.get("/api/swagger.json").status_code == 200
    out = c.post("/api/swagger/logout/", data='{}', content_type="application/json", HTTP_X_CSRFTOKEN=csrf)
    assert out.status_code == 200
    assert c.get("/api/swagger.json").status_code == 401


@pytest.mark.django_db
def test_swagger_fails_closed_if_secret_unset(settings):
    settings.SWAGGER_PASSWORD = ""
    assert Client().get("/api/swagger.json").status_code == 503


@pytest.mark.django_db
def test_admin_auth_alone_cannot_open_swagger(admin_client, settings):
    settings.SWAGGER_PASSWORD = "swagger-testing-password-123456"
    assert admin_client.get("/api/swagger.json").status_code == 401
