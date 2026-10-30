"""Only the worker contacts Google, never the browser or HTTP request."""
import logging
from celery import shared_task
from django.apps import apps
from django.db import transaction
from django.utils import timezone
from .models import TranslationJob
from .provider import translate_fr_mg
from .services import find_graph_field

log=logging.getLogger(__name__)


@shared_task(bind=True, ignore_result=True, acks_late=True, max_retries=3, default_retry_delay=60)
def translate_field(self, job_id):
    try:
        with transaction.atomic():
            job=TranslationJob.objects.select_for_update().get(pk=job_id)
            if job.state not in (job.State.PENDING,):return
            job.state=job.State.RUNNING;job.attempts+=1
            job.save(update_fields=['state','attempts','updated_at'])
        translated=translate_fr_mg(job.source_text)
        if not translated.strip():raise ValueError('EMPTY_PROVIDER_TRANSLATION')
        with transaction.atomic():
            job=TranslationJob.objects.select_for_update().get(pk=job_id)
            if job.state!=job.State.RUNNING:return
            model=apps.get_model(job.target_type)
            obj=model.objects.select_for_update().filter(pk=job.target_id).first()
            if obj is None:
                job.state=job.State.STALE
            elif job.target_type=='content_api.BrouillonGraphe':
                graph=obj.graphe
                current, field=find_graph_field(graph,job.path)
                if current!=job.source_text:
                    job.state=job.State.STALE
                else:
                    if len(translated)>12000:raise ValueError('TRANSLATION_TOO_LONG')
                    field['mg']=translated
                    obj.graphe=graph;obj.revision+=1
                    obj.save(update_fields=['graphe','revision','updated_at'])
                    job.state=job.State.DONE
            else:
                fr_key=job.path[0]
                mg_key=fr_key[:-3]+'_mg'
                current=getattr(obj,fr_key,None)
                if current!=job.source_text:
                    job.state=job.State.STALE
                else:
                    field=model._meta.get_field(mg_key)
                    if field.max_length and len(translated)>field.max_length:
                        raise ValueError('TRANSLATION_TOO_LONG')
                    setattr(obj,mg_key,translated)
                    obj.full_clean()
                    obj.save(update_fields=[mg_key,'updated_at'])
                    job.state=job.State.DONE
            job.last_error='';job.save(update_fields=['state','last_error','updated_at'])
    except TranslationJob.DoesNotExist:
        return
    except Exception as exc:
        # Never log source text / personal content nor credentials.
        log.warning('Translation job %s failed: %s',job_id,type(exc).__name__)
        if self.request.retries<self.max_retries:
            TranslationJob.objects.filter(pk=job_id,state='RUNNING').update(state='PENDING',last_error=type(exc).__name__)
            raise self.retry(exc=exc,countdown=min(3600,60*(2**self.request.retries)))
        TranslationJob.objects.filter(pk=job_id).exclude(state='STALE').update(state='FAILED',last_error=type(exc).__name__)
