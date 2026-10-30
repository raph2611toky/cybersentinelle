from uuid import UUID
from django.apps import apps
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAdminUser
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from apps.core.editor_service import ensure_model_permission,handle_editor_exception
from .models import TranslationJob
from .services import job_summary,dispatch_jobs
from .swagger import status_doc,retry_doc

ALLOWED = {'content_api.Visuel','content_api.Tantara','content_api.BrouillonGraphe','content_api.Sujet','pedagogie.QuestionPedagogique','resources.Source','resources.RessourceAide'}


def target_from(request):
    label=request.data.get('target_type') if request.method=='POST' else request.query_params.get('target_type')
    pk=request.data.get('target_id') if request.method=='POST' else request.query_params.get('target_id')
    if label not in ALLOWED:raise ValidationError({'target_type':['Type inconnu']})
    if label=='content_api.BrouillonGraphe':
        try:uuid=int(str(pk))
        except (TypeError,ValueError):raise ValidationError({'target_id':['Identifiant de graphe invalide']})
        if uuid<1:raise ValidationError({'target_id':['Identifiant de graphe invalide']})
    else:
        try:uuid=UUID(str(pk))
        except (TypeError,ValueError):raise ValidationError({'target_id':['UUID invalide']})
    model=apps.get_model(label)
    obj=get_object_or_404(model,pk=uuid)
    ensure_model_permission(request,model,'view')
    return label,obj


class TranslationStatusAPIView(APIView):
    permission_classes=[IsAdminUser]
    @status_doc
    def get(self,request):
        try:
            label,obj=target_from(request)
            return Response(job_summary(label,obj.pk))
        except Exception as exc:return handle_editor_exception(exc)


class TranslationRetryAPIView(APIView):
    permission_classes=[IsAdminUser]
    @retry_doc
    def post(self,request):
        try:
            label,obj=target_from(request)
            ensure_model_permission(request,type(obj),'change')
            ids=list(TranslationJob.objects.filter(target_type=label,target_id=obj.pk,state='FAILED').values_list('id',flat=True))
            TranslationJob.objects.filter(id__in=ids).update(state='PENDING',last_error='')
            # No waiting for provider. Queue availability is reported in worker logs.
            dispatch_jobs(ids)
            return Response({'requeued':len(ids)})
        except Exception as exc:return handle_editor_exception(exc)
