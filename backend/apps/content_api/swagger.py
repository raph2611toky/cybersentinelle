"""Toutes les descriptions drf-yasg sont séparées des classes APIView."""

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from helpers.api.swagger import ERROR_RESPONSES

str_field = lambda description="": openapi.Schema(
    type=openapi.TYPE_STRING, description=description
)
lang = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["fr", "mg"],
    properties={"fr": str_field(), "mg": str_field()},
)
option = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["id", "label", "feedback", "quality", "next"],
    properties={
        "id": str_field(),
        "label": lang,
        "feedback": lang,
        "quality": openapi.Schema(type=openapi.TYPE_NUMBER, minimum=0, maximum=1),
        "next": str_field(),
    },
)
node = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["kind", "title", "text"],
    properties={
        "kind": openapi.Schema(
            type=openapi.TYPE_STRING, enum=["scene", "decision", "ending"]
        ),
        "title": lang,
        "text": lang,
        "tag": str_field("Scène uniquement"),
        "visual": str_field("Identifiant visuel statique"),
        "visual_url": str_field("URL absolue si visuel présent"),
        "next": str_field("Transition scène uniquement"),
        "weight": openapi.Schema(
            type=openapi.TYPE_INTEGER, description="Décision uniquement"
        ),
        "options": openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=option,
            description="2 ou 3 options pour une décision",
        ),
    },
)
properties = {
    "id": str_field(),
    "number": str_field(),
    "title": lang,
    "subtitle": lang,
    "theme": lang,
    "description": lang,
    "warning": lang,
    "duration": str_field(),
    "expectedDecisions": openapi.Schema(type=openapi.TYPE_INTEGER),
    "palette": str_field(),
    "heroVisual": str_field(),
    "cover": str_field("Chemin versionné de la couverture publiée"),
    "cover_url": str_field("URL publique de la couverture publiée (si disponible)"),
    "heroVisual_url": str_field("URL absolue si fichier présent"),
}
required = [
    "id",
    "number",
    "title",
    "subtitle",
    "theme",
    "description",
    "warning",
    "duration",
    "expectedDecisions",
    "palette",
    "heroVisual",
]
story_summary = openapi.Schema(
    type=openapi.TYPE_OBJECT, required=required, properties=properties
)
story_detail = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=required + ["nodes"],
    properties={
        **properties,
        "nodes": openapi.Schema(type=openapi.TYPE_OBJECT, additional_properties=node),
    },
)
story_list_doc = swagger_auto_schema(
    tags=["Tantara"],
    operation_summary="Liste des Tantara publiés",
    operation_description="GET sans identité, réponses bilingues. HEAD et OPTIONS également supportés.",
    responses={
        200: openapi.Response(
            "Catalogue public",
            openapi.Schema(type=openapi.TYPE_ARRAY, items=story_summary),
        ),
        304: openapi.Response("ETag non modifié (sans corps)"),
        **ERROR_RESPONSES,
        503: openapi.Response("Aucune release active", ERROR_RESPONSES[500].schema),
    },
)
story_detail_doc = swagger_auto_schema(
    tags=["Tantara"],
    operation_summary="Graphe narratif complet",
    operation_description="Slug public d’un Tantara présent dans la release active.",
    responses={
        200: openapi.Response("Récit intégral", story_detail),
        304: openapi.Response("ETag non modifié (sans corps)"),
        **ERROR_RESPONSES,
        503: openapi.Response("Aucune release active", ERROR_RESPONSES[500].schema),
    },
)

# Documentation des vues éditoriales (indépendante de views.py).
from apps.core.editor_swagger import editor_swagger_docs, visual_form_parameters
from .serializers import SujetEditorSerializer, VisuelEditorSerializer, TantaraEditorSerializer, NoeudEditorSerializer, OptionDecisionEditorSerializer

sujet_docs = editor_swagger_docs("Sujet", SujetEditorSerializer)

visuel_docs = editor_swagger_docs("Visuel", VisuelEditorSerializer, multipart=True, manual_parameters=visual_form_parameters())

def tantara_form_parameters(*, required_fields=True):
    """Swagger 2.0 multipart : manuel, sans request_body (fichier dans formData)."""
    fields = [
        ("slug", openapi.TYPE_STRING), ("numero", openapi.TYPE_STRING),
        ("titre_fr", openapi.TYPE_STRING), ("sous_titre_fr", openapi.TYPE_STRING),
        ("theme_fr", openapi.TYPE_STRING), ("description_fr", openapi.TYPE_STRING),
        ("avertissement_fr", openapi.TYPE_STRING),
        ("duree", openapi.TYPE_STRING), ("decisions_attendues", openapi.TYPE_INTEGER),
        ("palette", openapi.TYPE_STRING), ("ordre", openapi.TYPE_INTEGER),
        ("image_cover", openapi.TYPE_FILE), ("effacer_couverture", openapi.TYPE_BOOLEAN),
        ("visuel_heros", openapi.TYPE_STRING),
        ("revision", openapi.TYPE_STRING),
        ("statut_editorial", openapi.TYPE_STRING),
        ("valide_le", openapi.TYPE_STRING),
        ("validateur_role", openapi.TYPE_STRING),
        ("relecture_fr_le", openapi.TYPE_STRING),
        ("relecture_mg_le", openapi.TYPE_STRING),
        ("relecteur_fr_role", openapi.TYPE_STRING),
        ("relecteur_mg_role", openapi.TYPE_STRING),
        ("note_validation", openapi.TYPE_STRING),
    ]
    mandatory = {
        "slug", "numero", "titre_fr", "sous_titre_fr", "theme_fr",
        "description_fr", "avertissement_fr", "duree", "decisions_attendues", "palette"
    } if required_fields else set()
    return [
        openapi.Parameter(
            name, openapi.IN_FORM, type=kind, required=name in mandatory,
            description=(
                "Couverture facultative PNG/JPEG/WebP, max. 5 Mo ; réencodée en PNG."
                if name == "image_cover" else
                "true pour supprimer la couverture actuelle (exclusif de image_cover)."
                if name == "effacer_couverture" else
                "Durée au format « 6 min »." if name == "duree" else
                "Texte source FR : traduction MG en file d'attente." if name.endswith("_fr") else
                "Champ du formulaire Tantara."
            ),
        ) for name, kind in fields
    ]


tantara_docs = editor_swagger_docs(
    "Tantara", TantaraEditorSerializer, multipart=True,
    manual_parameters=tantara_form_parameters(),
    partial_parameters=tantara_form_parameters(required_fields=False),
)

noeud_docs = editor_swagger_docs("Noeud", NoeudEditorSerializer)

optiondecision_docs = editor_swagger_docs("OptionDecision", OptionDecisionEditorSerializer)


published_cover_doc = swagger_auto_schema(
    tags=["Tantara"],
    operation_summary="Couverture PNG d'une release publiée",
    responses={200: openapi.Response("Image PNG versionnée"), 404: "Introuvable", 503: "Release invalide"},
)
