"""Endpoints APIView explicites : brouillon graphique, sauvegarde, application."""
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from apps.content_api.models import Tantara, Noeud, OptionDecision, BrouillonGraphe
from apps.content_api.graph_service import sanitize_graph, relational_graph, apply_graph
from apps.core.editor_service import ensure_model_permission, handle_editor_exception
from helpers.api.responses import error
from .graph_swagger import read_doc, save_doc, apply_doc
from apps.translation.services import prime_graph,create_jobs,job_summary,ensure_ready,obsolete_graph_jobs

class GraphReadAPIView(APIView):
    permission_classes=[IsAdminUser]
    @read_doc
    def get(self,request,pk):
        try:
            ensure_model_permission(request,Tantara,'view')
            story=get_object_or_404(Tantara,pk=pk)
            ensure_model_permission(request,Noeud,'view')
            ensure_model_permission(request,OptionDecision,'view')
            draft=BrouillonGraphe.objects.filter(tantara=story).first()
            return Response({'graph':draft.graphe if draft else relational_graph(story),'revision':draft.revision if draft else 0, 'draft_id':str(draft.pk) if draft else None,
                'translation_state':job_summary('content_api.BrouillonGraphe',draft.pk) if draft else {'state':'NONE','pending':0,'failed':0,'translated':0}})
        except Exception as exc:return handle_editor_exception(exc)

class GraphSaveAPIView(APIView):
    permission_classes=[IsAdminUser]
    @save_doc
    def put(self,request,pk):
        try:
            ensure_model_permission(request,Tantara,'change')
            graph=sanitize_graph(request.data.get('graph'))
            revision=request.data.get('revision')
            if not isinstance(revision,int) or isinstance(revision,bool) or revision<0:
                return error(400,'BAD_REQUEST','Révision de brouillon requise')
            with transaction.atomic():
                story=get_object_or_404(Tantara.objects.select_for_update(),pk=pk)
                draft=BrouillonGraphe.objects.select_for_update().filter(tantara=story).first()
                current=draft.revision if draft else 0
                if revision!=current:
                    return error(409,'VERSION_CONFLICT','Brouillon modifié ailleurs : recharger avant de sauver')
                previous=draft.graphe if draft else relational_graph(story)
                translations=prime_graph(graph,previous)
                if draft:
                    draft.graphe=graph;draft.revision+=1;draft.save()
                else:
                    draft=BrouillonGraphe.objects.create(tantara=story,graphe=graph,revision=1)
                obsolete_graph_jobs(draft,graph)
                create_jobs(draft,translations)
            return Response({'graph':draft.graphe,'revision':draft.revision,'draft_id':str(draft.pk),
                'translation_state':job_summary('content_api.BrouillonGraphe',draft.pk)})
        except Exception as exc:return handle_editor_exception(exc)

class GraphApplyAPIView(APIView):
    permission_classes=[IsAdminUser]
    @apply_doc
    def post(self,request,pk):
        try:
            ensure_model_permission(request,Tantara,'change')
            story=get_object_or_404(Tantara,pk=pk)
            # Application destructive/transactionnelle : permissions nécessaires sur
            # les nœuds et les options, pas seulement une permission de lecture.
            for model, actions in ((Noeud, ('view','add','change','delete')),
                                   (OptionDecision, ('view','add','change','delete'))):
                for action in actions:
                    ensure_model_permission(request,model,action)
            draft=get_object_or_404(BrouillonGraphe,tantara=story)
            ensure_ready('content_api.Tantara',story.pk)
            ensure_ready('content_api.BrouillonGraphe',draft.pk)
            count=apply_graph(story,draft.graphe)
            return Response({'applied':True,'nodes':count,'message':'Graphe appliqué ; relecture et approbation requises avant publication.'})
        except Exception as exc:return handle_editor_exception(exc)
