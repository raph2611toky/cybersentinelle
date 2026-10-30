"""Format d'erreur unique pour tous les handlers publics."""

import hashlib
import json
import logging
from django.http import HttpResponse
from rest_framework.response import Response

LOG = logging.getLogger("safidiko")


def error(status, code, message, *, fields=None):
    payload = {"error": {"code": code, "message": message}}
    if fields is not None:
        payload["error"]["fields"] = fields
    return Response(payload, status=status)


def failed(exc):
    # Aucun message d'exception renvoyé à un visiteur.
    LOG.exception("Erreur interne lors de la lecture de contenu public")
    return error(500, "INTERNAL_ERROR", "Erreur interne du serveur")


def public_json(request, data, *, max_age=300):
    blob = json.dumps(
        data, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    etag = '"' + hashlib.sha256(blob).hexdigest() + '"'
    if etag in [x.strip() for x in request.headers.get("If-None-Match", "").split(",")]:
        response = HttpResponse(status=304)
    else:
        response = Response(data, status=200)
    response["ETag"] = etag
    response["Cache-Control"] = f"public, max-age={max_age}"
    return response
