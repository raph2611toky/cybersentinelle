"""Décorateurs Swagger, indépendants des vues ; réponses alignées sur les payloads réels."""
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from .serializers import (MediaAssetSerializer, SceneSerializer, VoiceSerializer, JobSerializer, DialogueSerializer,
    MediaListResponseSerializer, SceneListResponseSerializer,
    MediaMetadataInput, VoiceListResponseSerializer,
    JobListResponseSerializer, DialogueListResponseSerializer)

ERROR = openapi.Schema(type=openapi.TYPE_OBJECT, required=['error'], properties={
    'error': openapi.Schema(type=openapi.TYPE_OBJECT, required=['code', 'message'], properties={
        'code': openapi.Schema(type=openapi.TYPE_STRING),
        'message': openapi.Schema(type=openapi.TYPE_STRING),
        'fields': openapi.Schema(type=openapi.TYPE_OBJECT),
    })
})

def responses(success, code=200, *, binary=False):
    result = {code: openapi.Response('Fichier en flux sécurisé' if binary else 'Succès',
                                   schema=None if binary else success),
              400: openapi.Response('Entrée invalide', ERROR),
              401: openapi.Response('Authentification requise', ERROR),
              403: openapi.Response('Permission insuffisante', ERROR),
              404: openapi.Response('Ressource introuvable', ERROR),
              405: openapi.Response('Méthode interdite', ERROR),
              409: openapi.Response('Conflit', ERROR),
              415: openapi.Response('Format non pris en charge', ERROR),
              413: openapi.Response('Fichier trop volumineux', ERROR),
              429: openapi.Response('Quota atteint', ERROR),
              500: openapi.Response('Erreur interne', ERROR),
              503: openapi.Response('Dépendance indisponible', ERROR)}
    return result


def obj(serializer):
    return serializer()


media_list_doc = swagger_auto_schema(operation_summary='Lister les médias privés du studio', tags=['Studio / Médias'], responses=responses(MediaListResponseSerializer()))
media_detail_doc = swagger_auto_schema(operation_summary='Détail d’un média privé', tags=['Studio / Médias'], responses=responses(obj(MediaAssetSerializer)))
media_download_doc = swagger_auto_schema(operation_summary='Télécharger un fichier privé (réponse binaire)', tags=['Studio / Médias'], produces=['application/octet-stream'], responses=responses(None, binary=True))
media_upload_doc = swagger_auto_schema(operation_summary='Importer un média image, audio, vidéo ou sous-titres', tags=['Studio / Médias'],
    consumes=['multipart/form-data'], manual_parameters=[
      openapi.Parameter('titre', openapi.IN_FORM, type=openapi.TYPE_STRING, required=True),
      openapi.Parameter('type', openapi.IN_FORM, type=openapi.TYPE_STRING, required=True, enum=['IMAGE', 'VIDEO', 'AUDIO', 'SUBTITLE']),
      openapi.Parameter('licence', openapi.IN_FORM, type=openapi.TYPE_STRING, required=True),
      openapi.Parameter('droits_confirmes', openapi.IN_FORM, type=openapi.TYPE_BOOLEAN, required=True),
      openapi.Parameter('langue', openapi.IN_FORM, type=openapi.TYPE_STRING, required=False, enum=['fr','mg']),
      openapi.Parameter('fichier', openapi.IN_FORM, type=openapi.TYPE_FILE, required=True),
    ], responses=responses(obj(MediaAssetSerializer), 201))
media_update_doc = swagger_auto_schema(operation_summary='Modifier les métadonnées d’un média privé (sans remplacer le fichier)', tags=['Studio / Médias'], request_body=MediaMetadataInput, responses=responses(obj(MediaAssetSerializer)))
media_delete_doc = swagger_auto_schema(operation_summary='Supprimer un média non utilisé', tags=['Studio / Médias'], responses=responses(
    openapi.Schema(type=openapi.TYPE_OBJECT, properties={'deleted': openapi.Schema(type=openapi.TYPE_BOOLEAN)})))
scene_list_doc = swagger_auto_schema(operation_summary='Lister les médias des nœuds (filtre ?noeud=UUID)', tags=['Studio / Scènes'], responses=responses(SceneListResponseSerializer()))
scene_detail_doc = swagger_auto_schema(operation_summary='Consulter le montage d’un nœud', tags=['Studio / Scènes'], responses=responses(obj(SceneSerializer)))
scene_create_doc = swagger_auto_schema(operation_summary='Créer le montage d’une scène ou d’une fin', tags=['Studio / Scènes'], request_body=SceneSerializer, responses=responses(obj(SceneSerializer), 201))
scene_patch_doc = swagger_auto_schema(operation_summary='Modifier le montage d’une scène ou d’une fin', tags=['Studio / Scènes'], request_body=SceneSerializer, responses=responses(obj(SceneSerializer)))
voice_list_doc = swagger_auto_schema(operation_summary='Lister les profils vocaux', tags=['Studio / Voix'], responses=responses(VoiceListResponseSerializer()))
voice_create_doc = swagger_auto_schema(operation_summary='Enregistrer une voix Gemini / ElevenLabs', tags=['Studio / Voix'], request_body=VoiceSerializer, responses=responses(obj(VoiceSerializer), 201))
tts_doc = swagger_auto_schema(operation_summary='Mettre en file une génération TTS FR/MG', tags=['Studio / Voix'],
  request_body=openapi.Schema(type=openapi.TYPE_OBJECT, required=['scene','voix','texte'], properties={
    'scene': openapi.Schema(type=openapi.TYPE_STRING, format='uuid'),
    'voix': openapi.Schema(type=openapi.TYPE_STRING, format='uuid'),
    'texte': openapi.Schema(type=openapi.TYPE_STRING)}), responses=responses(obj(JobSerializer), 202))
render_doc = swagger_auto_schema(operation_summary='Mettre en file un assemblage vidéo FFmpeg', tags=['Studio / Scènes'],
  request_body=openapi.Schema(type=openapi.TYPE_OBJECT), responses=responses(obj(JobSerializer), 202))
job_list_doc = swagger_auto_schema(operation_summary='Lister les travaux du studio', tags=['Studio / Tâches'], responses=responses(JobListResponseSerializer()))
job_detail_doc = swagger_auto_schema(operation_summary='Consulter le résultat d’une tâche', tags=['Studio / Tâches'], responses=responses(obj(JobSerializer)))
dialogue_list_doc = swagger_auto_schema(operation_summary='Lister les dialogues d’une scène', tags=['Studio / Dialogues'], responses=responses(DialogueListResponseSerializer()))
dialogue_create_doc = swagger_auto_schema(operation_summary='Ajouter une réplique', tags=['Studio / Dialogues'], request_body=DialogueSerializer, responses=responses(obj(DialogueSerializer), 201))
dialogue_patch_doc = swagger_auto_schema(operation_summary='Modifier une réplique', tags=['Studio / Dialogues'], request_body=DialogueSerializer, responses=responses(obj(DialogueSerializer)))
dialogue_delete_doc = swagger_auto_schema(operation_summary='Retirer une réplique', tags=['Studio / Dialogues'], responses=responses(
  openapi.Schema(type=openapi.TYPE_OBJECT, properties={'deleted':openapi.Schema(type=openapi.TYPE_BOOLEAN)})))

media_rights_doc = swagger_auto_schema(operation_summary='Confirmer les droits de diffusion d’un média après vérification',
    tags=['Studio / Médias'],
    request_body=openapi.Schema(type=openapi.TYPE_OBJECT, required=['licence'], properties={
        'licence': openapi.Schema(type=openapi.TYPE_STRING, description='Licence effectivement vérifiée par l’éditeur')
    }), responses=responses(obj(MediaAssetSerializer)))


dialogue_tts_doc = swagger_auto_schema(operation_summary='Générer une voix pour une réplique via son profil vocal',
    tags=['Studio / Dialogues'], request_body=openapi.Schema(type=openapi.TYPE_OBJECT),
    responses=responses(obj(JobSerializer), 202))

voice_detail_doc = swagger_auto_schema(operation_summary='Détail d’un profil vocal', tags=['Studio / Voix'], responses=responses(obj(VoiceSerializer)))
voice_patch_doc = swagger_auto_schema(operation_summary='Modifier un profil vocal', tags=['Studio / Voix'], request_body=VoiceSerializer, responses=responses(obj(VoiceSerializer)))
voice_delete_doc = swagger_auto_schema(operation_summary='Supprimer un profil vocal non référencé', tags=['Studio / Voix'], responses=responses(
    openapi.Schema(type=openapi.TYPE_OBJECT, properties={'deleted': openapi.Schema(type=openapi.TYPE_BOOLEAN)})))
scene_delete_doc = swagger_auto_schema(operation_summary='Supprimer le montage d’une scène', tags=['Studio / Scènes'], responses=responses(
    openapi.Schema(type=openapi.TYPE_OBJECT, properties={'deleted': openapi.Schema(type=openapi.TYPE_BOOLEAN)})))
