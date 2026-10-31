from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from helpers.api.swagger import ERROR_RESPONSES

public_media_doc = swagger_auto_schema(
    operation_summary='Lire un clip d’une publication validée (réponse binaire)',
    tags=['Tantara / Médias publics'],
    produces=['video/mp4', 'audio/mpeg'],
    responses={
        200: openapi.Response('Flux MP4 vidéo ou MP3 audio publié (aucun corps JSON)'),
        206: openapi.Response('Plage de lecture partielle'),
        416: openapi.Response('Plage invalide, corps vide'),
        **ERROR_RESPONSES,
        503: openapi.Response('Publication non disponible', ERROR_RESPONSES[500].schema),
    },
)


public_subtitle_doc = swagger_auto_schema(
    operation_summary='Lire les sous-titres publiés (réponse binaire)',
    tags=['Tantara / Médias publics'],
    produces=['text/vtt', 'application/x-subrip'],
    responses={200: openapi.Response('Flux de sous-titres (aucun corps JSON)'), **ERROR_RESPONSES,
               503: openapi.Response('Publication non disponible', ERROR_RESPONSES[500].schema)},
)
