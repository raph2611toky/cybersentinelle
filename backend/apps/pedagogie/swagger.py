from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from config.swagger import ERROR_RESPONSES
from apps.content_api.swagger import lang

q = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["id", "topic", "question", "answer", "reviewStatus", "version"],
    properties={
        "id": openapi.Schema(type=openapi.TYPE_STRING),
        "topic": openapi.Schema(type=openapi.TYPE_STRING),
        "question": lang,
        "answer": lang,
        "reviewStatus": openapi.Schema(type=openapi.TYPE_STRING, enum=["approved"]),
        "version": openapi.Schema(type=openapi.TYPE_STRING),
    },
)
questions_doc = swagger_auto_schema(
    tags=["Pédagogie"],
    operation_summary="Questions validées",
    responses={
        200: openapi.Response(
            "Questions bilingues", openapi.Schema(type=openapi.TYPE_ARRAY, items=q)
        ),
        304: openapi.Response("ETag non modifié (sans corps)"),
        **ERROR_RESPONSES,
        503: openapi.Response("Aucune release active", ERROR_RESPONSES[500].schema),
    },
)
