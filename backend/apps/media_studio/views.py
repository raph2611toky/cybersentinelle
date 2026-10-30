"""Une classe APIView et une seule méthode HTTP par opération. Aucun ViewSet."""
import logging
from pathlib import Path
from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError, RestrictedError
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.core.models import Langue
from helpers.api.responses import error, failed
from .models import MediaAsset, VoiceProfile, SceneMedia, GenerationJob, DialogueLine
from .permissions import StudioPermissions
from .serializers import (MediaAssetSerializer, MediaUploadInput, VoiceSerializer,
    SceneSerializer, DialogueSerializer, JobSerializer, TTSInput)
from .services.media import persist_upload
from .tasks import process_studio_job
from . import swagger as docs

LOG = logging.getLogger('safidiko')


def invalid(exc):
    if isinstance(exc, serializers.ValidationError):
        details = exc.detail
    elif hasattr(exc, 'message_dict'):
        details = exc.message_dict
    else:
        details = {'non_field_errors': getattr(exc, 'messages', ['Requête invalide'])}
    return error(400, 'BAD_REQUEST', 'Requête invalide', fields=details)


def conflict():
    return error(409, 'CONFLICT', 'Objet lié ou opération incompatible avec l’état actuel')


class StudioQueueUnavailable(Exception):
    pass


def enqueue(job):
    # Le broker indisponible ne laisse pas une tâche indéfiniment PENDING.
    try:
        process_studio_job.delay(str(job.pk))
    except Exception:
        LOG.exception('File de tâches du studio indisponible')
        GenerationJob.objects.filter(pk=job.pk).update(statut=GenerationJob.Status.FAILED,
            code_erreur='QUEUE_UNAVAILABLE', fin_le=timezone.now())
        raise StudioQueueUnavailable() from None
    return job


class MediaListAPIView(APIView):
    permission_classes = [StudioPermissions]
    required_permission = 'media_studio.view_mediaasset'

    @docs.media_list_doc
    def get(self, request):
        try:
            items = MediaAsset.objects.select_related('langue').all()[:200]
            return Response({'results': MediaAssetSerializer(items, many=True, context={'request': request}).data})
        except Exception as exc:
            return failed(exc)


class MediaDetailAPIView(APIView):
    permission_classes = [StudioPermissions]
    required_permission = 'media_studio.view_mediaasset'

    @docs.media_detail_doc
    def get(self, request, pk):
        try:
            obj = get_object_or_404(MediaAsset.objects.select_related('langue'), pk=pk)
            return Response(MediaAssetSerializer(obj, context={'request': request}).data)
        except Exception as exc:
            if isinstance(exc, Http404):
                return error(404, 'NOT_FOUND', 'Média introuvable')
            return failed(exc)


class MediaFileAPIView(APIView):
    permission_classes = [StudioPermissions]
    required_permission = 'media_studio.view_mediaasset'

    @docs.media_download_doc
    def get(self, request, pk):
        try:
            obj = get_object_or_404(MediaAsset, pk=pk)
            file = obj.fichier.open('rb')
            response = FileResponse(file, content_type=obj.mime_type, as_attachment=False)
            response['Cache-Control'] = 'private, no-store'
            response['Content-Disposition'] = f'inline; filename="media-{obj.pk}{Path(obj.fichier.name).suffix}"'
            return response
        except Exception as exc:
            if isinstance(exc, Http404):
                return error(404, 'NOT_FOUND', 'Média introuvable')
            return failed(exc)


class MediaUploadAPIView(APIView):
    permission_classes = [StudioPermissions]
    required_permission = 'media_studio.add_mediaasset'
    parser_classes = [MultiPartParser, FormParser]

    @docs.media_upload_doc
    def post(self, request):
        try:
            inp = MediaUploadInput(data=request.data)
            inp.is_valid(raise_exception=True)
            p = inp.validated_data
            if p['droits_confirmes'] is not True:
                return error(400, 'BAD_REQUEST', 'Droits non confirmés', fields={'droits_confirmes': ['Obligatoire']})
            language = None
            if p.get('langue'):
                language = Langue.objects.filter(code=p['langue'], actif=True).first()
                if language is None:
                    return error(400, 'BAD_REQUEST', 'Langue invalide', fields={'langue': ['Choisir fr ou mg']})
            asset = persist_upload(p['fichier'], p['type'], p['titre'], p['licence'], langue=language)
            return Response(MediaAssetSerializer(asset, context={'request': request}).data, status=201)
        except (serializers.ValidationError, DjangoValidationError) as exc:
            return invalid(exc)
        except Exception as exc:
            return failed(exc)


class MediaDeleteAPIView(APIView):
    permission_classes = [StudioPermissions]
    required_permission = 'media_studio.delete_mediaasset'

    @docs.media_delete_doc
    def delete(self, request, pk):
        try:
            obj = get_object_or_404(MediaAsset, pk=pk)
            with transaction.atomic():
                obj.delete()
            obj.fichier.delete(save=False)
            return Response({'deleted': True})
        except (ProtectedError, RestrictedError, IntegrityError):
            return conflict()
        except Exception as exc:
            if isinstance(exc, Http404):
                return error(404, 'NOT_FOUND', 'Média introuvable')
            return failed(exc)


class SceneListAPIView(APIView):
    permission_classes = [StudioPermissions]
    required_permission = 'media_studio.view_scenemedia'

    @docs.scene_list_doc
    def get(self, request):
        try:
            qs = SceneMedia.objects.select_related('noeud', 'langue').all()
            if request.query_params.get('noeud'):
                import uuid
                try:
                    node_id = uuid.UUID(request.query_params['noeud'])
                except ValueError:
                    return error(400, 'BAD_REQUEST', 'UUID du nœud invalide')
                qs = qs.filter(noeud_id=node_id)
            return Response({'results': SceneSerializer(qs[:200], many=True, context={'request': request}).data})
        except Exception as exc:
            return failed(exc)


class SceneDetailAPIView(APIView):
    permission_classes = [StudioPermissions]
    required_permission = 'media_studio.view_scenemedia'

    @docs.scene_detail_doc
    def get(self, request, pk):
        try:
            obj = get_object_or_404(SceneMedia, pk=pk)
            return Response(SceneSerializer(obj, context={'request': request}).data)
        except Exception as exc:
            if isinstance(exc, Http404):
                return error(404, 'NOT_FOUND', 'Scène introuvable')
            return failed(exc)


class SceneCreateAPIView(APIView):
    permission_classes = [StudioPermissions]
    required_permission = 'media_studio.add_scenemedia'

    @docs.scene_create_doc
    def post(self, request):
        try:
            s = SceneSerializer(data=request.data, context={'request': request})
            s.is_valid(raise_exception=True)
            obj = s.save()
            return Response(SceneSerializer(obj, context={'request': request}).data, status=201)
        except (serializers.ValidationError, DjangoValidationError) as exc:
            return invalid(exc)
        except IntegrityError:
            return conflict()
        except Exception as exc:
            return failed(exc)


class ScenePatchAPIView(APIView):
    permission_classes = [StudioPermissions]
    required_permission = 'media_studio.change_scenemedia'

    @docs.scene_patch_doc
    def patch(self, request, pk):
        try:
            obj = get_object_or_404(SceneMedia, pk=pk)
            if obj.jobs.filter(statut__in=['PENDING', 'RUNNING']).exists():
                return conflict()
            s = SceneSerializer(obj, data=request.data, partial=True, context={'request': request})
            s.is_valid(raise_exception=True)
            obj = s.save(video_finale=None, statut=SceneMedia.Status.DRAFT)
            return Response(SceneSerializer(obj, context={'request': request}).data)
        except (serializers.ValidationError, DjangoValidationError) as exc:
            return invalid(exc)
        except IntegrityError:
            return conflict()
        except Exception as exc:
            if isinstance(exc, Http404):
                return error(404, 'NOT_FOUND', 'Scène introuvable')
            return failed(exc)


class VoiceListAPIView(APIView):
    permission_classes = [StudioPermissions]
    required_permission = 'media_studio.view_voiceprofile'

    @docs.voice_list_doc
    def get(self, request):
        try:
            return Response({'results': VoiceSerializer(VoiceProfile.objects.select_related('langue').all()[:200], many=True).data})
        except Exception as exc:
            return failed(exc)


class VoiceCreateAPIView(APIView):
    permission_classes = [StudioPermissions]
    required_permission = 'media_studio.add_voiceprofile'

    @docs.voice_create_doc
    def post(self, request):
        try:
            s = VoiceSerializer(data=request.data)
            s.is_valid(raise_exception=True)
            obj = s.save()
            return Response(VoiceSerializer(obj).data, status=201)
        except (serializers.ValidationError, DjangoValidationError) as exc:
            return invalid(exc)
        except IntegrityError:
            return conflict()
        except Exception as exc:
            return failed(exc)


class TTSCreateAPIView(APIView):
    permission_classes = [StudioPermissions]
    required_permission = 'media_studio.add_generationjob'

    @docs.tts_doc
    def post(self, request):
        try:
            s = TTSInput(data=request.data)
            s.is_valid(raise_exception=True)
            d = s.validated_data
            today = timezone.localdate()
            if GenerationJob.objects.filter(type='TTS', created_at__date=today).count() >= settings.STUDIO_TTS_DAILY_LIMIT:
                return error(429, 'TTS_DAILY_LIMIT', 'Limite quotidienne de synthèse vocale atteinte')
            job = GenerationJob.objects.create(type='TTS', scene=d['scene'], voix=d['voix'], texte=d['texte'])
            enqueue(job)
            return Response(JobSerializer(job, context={'request': request}).data, status=202)
        except StudioQueueUnavailable:
            return error(503, 'QUEUE_UNAVAILABLE', 'File de traitements indisponible')
        except (serializers.ValidationError, DjangoValidationError) as exc:
            return invalid(exc)
        except Exception as exc:
            return failed(exc)


class RenderCreateAPIView(APIView):
    permission_classes = [StudioPermissions]
    required_permission = 'media_studio.add_generationjob'

    @docs.render_doc
    def post(self, request, pk):
        try:
            scene = get_object_or_404(SceneMedia, pk=pk)
            if scene.mode == SceneMedia.Mode.TEXT_ONLY:
                return error(400, 'BAD_REQUEST', 'Aucun média à assembler')
            if scene.mode in {SceneMedia.Mode.IMAGE_AUDIO, SceneMedia.Mode.VIDEO_AUDIO} and not scene.audio_id:
                complete_lines = scene.dialogues.exists() and not scene.dialogues.filter(audio__isnull=True).exists()
                if not complete_lines and not (scene.voix_id and scene.narration_texte.strip()):
                    return error(400, 'BAD_REQUEST', 'Fournir un audio, les répliques sonorisées, ou une narration et une voix')
            if scene.jobs.filter(statut__in=['PENDING', 'RUNNING']).exists():
                return conflict()
            job = GenerationJob.objects.create(type='RENDER', scene=scene)
            scene.statut = SceneMedia.Status.PROCESSING
            scene.save(update_fields=['statut', 'updated_at'])
            enqueue(job)
            return Response(JobSerializer(job, context={'request': request}).data, status=202)
        except StudioQueueUnavailable:
            return error(503, 'QUEUE_UNAVAILABLE', 'File de traitements indisponible')
        except Exception as exc:
            if isinstance(exc, Http404):
                return error(404, 'NOT_FOUND', 'Scène introuvable')
            return failed(exc)


class JobListAPIView(APIView):
    permission_classes = [StudioPermissions]
    required_permission = 'media_studio.view_generationjob'

    @docs.job_list_doc
    def get(self, request):
        try:
            return Response({'results': JobSerializer(GenerationJob.objects.all()[:100], many=True, context={'request': request}).data})
        except Exception as exc:
            return failed(exc)


class JobDetailAPIView(APIView):
    permission_classes = [StudioPermissions]
    required_permission = 'media_studio.view_generationjob'

    @docs.job_detail_doc
    def get(self, request, pk):
        try:
            obj = get_object_or_404(GenerationJob, pk=pk)
            return Response(JobSerializer(obj, context={'request': request}).data)
        except Exception as exc:
            if isinstance(exc, Http404):
                return error(404, 'NOT_FOUND', 'Tâche introuvable')
            return failed(exc)


class DialogueListAPIView(APIView):
    permission_classes = [StudioPermissions]
    required_permission = 'media_studio.view_dialogueline'

    @docs.dialogue_list_doc
    def get(self, request, pk):
        try:
            scene = get_object_or_404(SceneMedia, pk=pk)
            return Response({'results': DialogueSerializer(scene.dialogues.all(), many=True).data})
        except Exception as exc:
            if isinstance(exc, Http404):
                return error(404, 'NOT_FOUND', 'Scène introuvable')
            return failed(exc)


class DialogueCreateAPIView(APIView):
    permission_classes = [StudioPermissions]
    required_permission = 'media_studio.add_dialogueline'

    @docs.dialogue_create_doc
    def post(self, request):
        try:
            s = DialogueSerializer(data=request.data)
            s.is_valid(raise_exception=True)
            obj = s.save()
            return Response(DialogueSerializer(obj).data, status=201)
        except (serializers.ValidationError, DjangoValidationError) as exc:
            return invalid(exc)
        except IntegrityError:
            return conflict()
        except Exception as exc:
            return failed(exc)


class DialoguePatchAPIView(APIView):
    permission_classes = [StudioPermissions]
    required_permission = 'media_studio.change_dialogueline'

    @docs.dialogue_patch_doc
    def patch(self, request, pk):
        try:
            obj = get_object_or_404(DialogueLine, pk=pk)
            s = DialogueSerializer(obj, data=request.data, partial=True)
            s.is_valid(raise_exception=True)
            obj = s.save()
            return Response(DialogueSerializer(obj).data)
        except (serializers.ValidationError, DjangoValidationError) as exc:
            return invalid(exc)
        except IntegrityError:
            return conflict()
        except Exception as exc:
            if isinstance(exc, Http404):
                return error(404, 'NOT_FOUND', 'Réplique introuvable')
            return failed(exc)


class DialogueDeleteAPIView(APIView):
    permission_classes = [StudioPermissions]
    required_permission = 'media_studio.delete_dialogueline'

    @docs.dialogue_delete_doc
    def delete(self, request, pk):
        try:
            get_object_or_404(DialogueLine, pk=pk).delete()
            return Response({'deleted': True})
        except (IntegrityError, ProtectedError, RestrictedError):
            return conflict()
        except Exception as exc:
            if isinstance(exc, Http404):
                return error(404, 'NOT_FOUND', 'Réplique introuvable')
            return failed(exc)


class MediaRightsConfirmAPIView(APIView):
    """La voix générée reste non publiable tant que l'éditeur n'a pas vérifié sa licence."""
    permission_classes = [StudioPermissions]
    required_permission = 'media_studio.change_mediaasset'

    @docs.media_rights_doc
    def post(self, request, pk):
        try:
            licence = request.data.get('licence', '')
            if not isinstance(licence, str) or not 3 <= len(licence.strip()) <= 160:
                return error(400, 'BAD_REQUEST', 'Licence vérifiée obligatoire')
            asset = get_object_or_404(MediaAsset, pk=pk)
            asset.licence = licence.strip()
            asset.droits_confirmes = True
            asset.full_clean()
            asset.save(update_fields=['licence', 'droits_confirmes', 'updated_at'])
            return Response(MediaAssetSerializer(asset, context={'request': request}).data)
        except (serializers.ValidationError, DjangoValidationError) as exc:
            return invalid(exc)
        except Exception as exc:
            if isinstance(exc, Http404):
                return error(404, 'NOT_FOUND', 'Média introuvable')
            return failed(exc)


class DialogueTTSCreateAPIView(APIView):
    permission_classes = [StudioPermissions]
    required_permission = 'media_studio.add_generationjob'

    @docs.dialogue_tts_doc
    def post(self, request, pk):
        try:
            dialogue = get_object_or_404(DialogueLine.objects.select_related('scene', 'voix', 'scene__langue'), pk=pk)
            if not dialogue.voix_id or not dialogue.voix.actif or dialogue.voix.langue_id != dialogue.scene.langue_id:
                return error(400, 'BAD_REQUEST', 'Voix valide requise pour cette réplique')
            if len(dialogue.texte) > settings.STUDIO_MAX_TTS_CHARS:
                return error(400, 'BAD_REQUEST', 'Texte trop long')
            today = timezone.localdate()
            if GenerationJob.objects.filter(type='TTS', created_at__date=today).count() >= settings.STUDIO_TTS_DAILY_LIMIT:
                return error(429, 'TTS_DAILY_LIMIT', 'Limite quotidienne de synthèse vocale atteinte')
            if dialogue.scene.jobs.filter(statut__in=['PENDING', 'RUNNING']).exists():
                return conflict()
            job = GenerationJob.objects.create(type='TTS', scene=dialogue.scene, dialogue=dialogue,
                voix=dialogue.voix, texte=dialogue.texte)
            enqueue(job)
            return Response(JobSerializer(job, context={'request': request}).data, status=202)
        except StudioQueueUnavailable:
            return error(503, 'QUEUE_UNAVAILABLE', 'File de traitements indisponible')
        except Exception as exc:
            if isinstance(exc, Http404):
                return error(404, 'NOT_FOUND', 'Réplique introuvable')
            return failed(exc)


class VoiceDetailAPIView(APIView):
    permission_classes = [StudioPermissions]
    required_permission = 'media_studio.view_voiceprofile'

    @docs.voice_detail_doc
    def get(self, request, pk):
        try:
            voice = get_object_or_404(VoiceProfile, pk=pk)
            return Response(VoiceSerializer(voice).data)
        except Exception as exc:
            if isinstance(exc, Http404):
                return error(404, 'NOT_FOUND', 'Voix introuvable')
            return failed(exc)


class VoicePatchAPIView(APIView):
    permission_classes = [StudioPermissions]
    required_permission = 'media_studio.change_voiceprofile'

    @docs.voice_patch_doc
    def patch(self, request, pk):
        try:
            voice = get_object_or_404(VoiceProfile, pk=pk)
            if voice.scenes.exists() or voice.dialogues.exists() or voice.generationjob_set.exists():
                return conflict()
            s = VoiceSerializer(voice, data=request.data, partial=True)
            s.is_valid(raise_exception=True)
            voice = s.save()
            return Response(VoiceSerializer(voice).data)
        except (serializers.ValidationError, DjangoValidationError) as exc:
            return invalid(exc)
        except IntegrityError:
            return conflict()
        except Exception as exc:
            if isinstance(exc, Http404):
                return error(404, 'NOT_FOUND', 'Voix introuvable')
            return failed(exc)


class VoiceDeleteAPIView(APIView):
    permission_classes = [StudioPermissions]
    required_permission = 'media_studio.delete_voiceprofile'

    @docs.voice_delete_doc
    def delete(self, request, pk):
        try:
            get_object_or_404(VoiceProfile, pk=pk).delete()
            return Response({'deleted': True})
        except (IntegrityError, ProtectedError, RestrictedError):
            return conflict()
        except Exception as exc:
            if isinstance(exc, Http404):
                return error(404, 'NOT_FOUND', 'Voix introuvable')
            return failed(exc)


class SceneDeleteAPIView(APIView):
    permission_classes = [StudioPermissions]
    required_permission = 'media_studio.delete_scenemedia'

    @docs.scene_delete_doc
    def delete(self, request, pk):
        try:
            scene = get_object_or_404(SceneMedia, pk=pk)
            if scene.jobs.filter(statut__in=['PENDING', 'RUNNING']).exists():
                return conflict()
            scene.delete()
            return Response({'deleted': True})
        except (IntegrityError, ProtectedError, RestrictedError):
            return conflict()
        except Exception as exc:
            if isinstance(exc, Http404):
                return error(404, 'NOT_FOUND', 'Scène introuvable')
            return failed(exc)
