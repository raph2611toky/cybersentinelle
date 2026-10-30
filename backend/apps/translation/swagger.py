"""OpenAPI: status/retry for editorial translations (staff + CSRF)."""
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

summary = openapi.Schema(type=openapi.TYPE_OBJECT, properties={
    'state': openapi.Schema(type=openapi.TYPE_STRING, enum=['NONE','PENDING','FAILED','REVIEW_REQUIRED']),
    'pending': openapi.Schema(type=openapi.TYPE_INTEGER),
    'failed': openapi.Schema(type=openapi.TYPE_INTEGER),
    'translated': openapi.Schema(type=openapi.TYPE_INTEGER),
})
status_doc = swagger_auto_schema(
    operation_description='État des traductions d’un objet éditorial staff. Aucune donnée de joueur.',
    tags=['Admin / traductions'],
    manual_parameters=[
        openapi.Parameter('target_type',openapi.IN_QUERY,type=openapi.TYPE_STRING,required=True),
        openapi.Parameter('target_id',openapi.IN_QUERY,type=openapi.TYPE_STRING,required=True),
    ],
    responses={200:summary,400:'Paramètres invalides',403:'Accès refusé',404:'Objet introuvable'},
)
retry_doc = swagger_auto_schema(
    operation_description='Relance les traductions FAILED en file, sans attendre la réponse du fournisseur.',
    tags=['Admin / traductions'],
    request_body=openapi.Schema(type=openapi.TYPE_OBJECT,required=['target_type','target_id'],properties={
        'target_type':openapi.Schema(type=openapi.TYPE_STRING),
        'target_id':openapi.Schema(type=openapi.TYPE_STRING),
    }),
    responses={200:openapi.Schema(type=openapi.TYPE_OBJECT,properties={'requeued':openapi.Schema(type=openapi.TYPE_INTEGER)}),403:'Accès refusé'},
)
