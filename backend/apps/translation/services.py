"""Scheduling, statuses and stale-proof updates; never translate in HTTP views."""
import logging
from django.db import transaction
from .models import TranslationJob

log = logging.getLogger(__name__)


def target_label(model):
    return model._meta.label


def create_jobs(obj, pairs):
    """Call inside the same DB transaction as the editorial update.

    pairs: iterable of (path: list[str], source_text: str).
    HTTP returns after commit, never after provider calls.
    """
    created = []
    for path, source in pairs:
        if not isinstance(source, str):
            continue
        TranslationJob.objects.filter(target_type=target_label(obj), target_id=obj.pk, path=path).exclude(
            state=TranslationJob.State.STALE
        ).update(state=TranslationJob.State.STALE)
        if not source.strip():
            continue
        created.append(TranslationJob.objects.create(
            target_type=target_label(obj), target_id=obj.pk, path=path,
            source_text=source, source_sha256=TranslationJob.fingerprint(source),
        ).pk)
    if created:
        transaction.on_commit(lambda ids=tuple(created): dispatch_jobs(ids))
    return created


def dispatch_jobs(job_ids):
    """Broker can be down; jobs remain PENDING for manual dispatcher/recovery."""
    from .tasks import translate_field
    for job_id in job_ids:
        try:
            translate_field.apply_async(args=(str(job_id),), queue='translation', retry=False)
        except Exception:
            log.exception('Translation broker unavailable; job %s remains pending', job_id)


def job_summary(target_type, target_id):
    qs = TranslationJob.objects.filter(target_type=target_type, target_id=target_id).exclude(state='STALE')
    states = list(qs.values_list('state', flat=True))
    counts = {state:states.count(state) for state in ('PENDING','RUNNING','DONE','FAILED')}
    if counts['FAILED']:
        state = 'FAILED'
    elif counts['PENDING'] or counts['RUNNING']:
        state = 'PENDING'
    elif counts['DONE']:
        state = 'REVIEW_REQUIRED'
    else:
        state = 'NONE'
    return {'state':state,'pending':counts['PENDING']+counts['RUNNING'], 'failed':counts['FAILED'], 'translated':counts['DONE']}


def ensure_ready(target_type, target_id):
    if TranslationJob.objects.filter(target_type=target_type, target_id=target_id,
                                     state__in=['PENDING','RUNNING','FAILED']).exists():
        from rest_framework.exceptions import ValidationError
        raise ValidationError({'translation':['Terminer ou relancer les traductions FR→MG avant cette action.']})


def find_graph_field(graph, path):
    """Return (source_fr, container_dict) or (None, None); IDs are stable."""
    if len(path) not in (3,5) or path[0]!='nodes': return None,None
    node = next((x for x in graph.get('nodes',[]) if x.get('id')==path[1]), None)
    if not node:return None,None
    data = node.get('data',{})
    if len(path)==3:
        container=data.get(path[2])
    elif path[3]=='options':
        opt=next((o for o in data.get('options',[]) if o.get('id')==path[4]), None)
        container=opt.get(path[2]) if opt else None
    else:container=None
    return (container.get('fr'),container) if isinstance(container,dict) else (None,None)


def prime_graph(current, previous):
    """Give the server French-only edits, retaining already translated unchanged nodes."""
    before={n['id']:n for n in (previous or {}).get('nodes',[])}
    changed=[]
    for node in current.get('nodes',[]):
        key=node['id']; data=node['data']; old=before.get(key,{}).get('data',{})
        for field in ('title','text'):
            fr=data.get(field,{}).get('fr','')
            old_fr=(old.get(field) or {}).get('fr','')
            if fr != old_fr:
                data[field]['mg']=fr
                changed.append((['nodes',key,field],fr))
            else:
                data[field]['mg']=(old.get(field) or {}).get('mg',data[field].get('mg',''))
        old_opts={o['id']:o for o in old.get('options',[])}
        for option in data.get('options',[]):
            prior=old_opts.get(option['id'],{})
            for field in ('label','feedback'):
                fr=option.get(field,{}).get('fr','')
                old_fr=(prior.get(field) or {}).get('fr','')
                if fr != old_fr:
                    option[field]['mg']=fr
                    changed.append((['nodes',key,field,'options',option['id']],fr))
                else:
                    option[field]['mg']=(prior.get(field) or {}).get('mg',option[field].get('mg',''))
    return changed


def obsolete_graph_jobs(draft, graph):
    """Stale queued fields removed from the current graph must not block apply."""
    qs=TranslationJob.objects.filter(target_type='content_api.BrouillonGraphe',
                                     target_id=draft.pk,state__in=['PENDING','RUNNING','FAILED'])
    for job in qs:
        source,_=find_graph_field(graph,job.path)
        if source!=job.source_text:
            qs.filter(pk=job.pk).update(state=TranslationJob.State.STALE)
