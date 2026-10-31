"""Brouillon React Flow + conversion explicite et transactionnelle en graphe relationnel."""
import re
import math
import uuid
from collections import defaultdict
from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework.exceptions import ValidationError as APIValidationError
from apps.core.choices import StatutEditorial
from apps.content_api.models import Noeud, OptionDecision, BrouillonGraphe
from apps.content_api.validation import validate_story_graph

SLUG = re.compile(r'^[a-z0-9][a-z0-9_-]{0,79}$')


def sanitize_graph(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get('nodes'), list) or not isinstance(payload.get('edges'), list):
        raise APIValidationError({'graph':['nodes et edges doivent être des tableaux']})
    if len(payload['nodes']) > 160 or len(payload['edges']) > 400:
        raise APIValidationError({'graph':['Graphe trop volumineux']})
    nodes = []
    identifiers = set()
    for index, item in enumerate(payload['nodes']):
        if not isinstance(item, dict):
            raise APIValidationError({'nodes':[f'Noeud {index} incorrect']})
        key = item.get('id')
        if not isinstance(key, str) or not SLUG.fullmatch(key) or key in identifiers:
            raise APIValidationError({'nodes':[f'Identifiant du nœud {index} invalide ou dupliqué']})
        identifiers.add(key)
        data = item.get('data', {})
        if not isinstance(data, dict) or data.get('kind') not in ('scene','decision','ending'):
            raise APIValidationError({'nodes':[f'Type invalide pour {key}']})
        def localized(attr):
            obj = data.get(attr) or {}
            if not isinstance(obj, dict): obj={}
            return {lang:str(obj.get(lang) or '')[:(255 if attr=='title' else 12000)] for lang in ('fr','mg')}
        options=[]
        for j,option in enumerate(data.get('options', []) if data.get('kind')=='decision' else []):
            if not isinstance(option, dict):raise APIValidationError({'options':['Option invalide']})
            oid=option.get('id')
            if not isinstance(oid,str) or not SLUG.fullmatch(oid) or oid in [x['id'] for x in options]:
                raise APIValidationError({'options':[f'Clé de choix invalide pour {key}']})
            def loc(k):
                pair=option.get(k, {})
                if not isinstance(pair,dict):pair={}
                return {l:str(pair.get(l) or '')[:12000] for l in ('fr','mg')}
            try:quality=float(option.get('quality',0))
            except (ValueError, TypeError):raise APIValidationError({'options':[f'Qualité invalide : {key}']})
            if not math.isfinite(quality):raise APIValidationError({'options':[f'Qualité non finie : {key}']})
            options.append({'id':oid,'label':loc('label'),'feedback':loc('feedback'),
                            'quality':max(0,min(1,quality))})
        pos=item.get('position') or {}
        if not isinstance(pos,dict):pos={}
        try:
            x,y=float(pos.get('x',0)),float(pos.get('y',0))
            weight=int(data.get('weight') or 20)
        except (ValueError,TypeError):raise APIValidationError({'nodes':[f'Position ou poids invalide : {key}']})
        if not all(math.isfinite(v) and abs(v)<1_000_000 for v in (x,y)):
            raise APIValidationError({'nodes':[f'Position hors limites : {key}']})
        # Le choix de média appartient au brouillon, avant même que le nœud ait un PK Django.
        media_choice = data.get('media')
        if media_choice is not None:
            if data['kind'] == 'decision' or not isinstance(media_choice, dict):
                raise APIValidationError({'media': [f'Média interdit ou invalide sur {key}']})
            if set(media_choice) != {'asset', 'kind'} or media_choice.get('kind') not in ('VIDEO', 'IMAGE'):
                raise APIValidationError({'media': [f'Type de média invalide sur {key}']})
            try:
                media_choice = {'asset': str(uuid.UUID(str(media_choice['asset']))), 'kind': media_choice['kind']}
            except (ValueError, TypeError, AttributeError):
                raise APIValidationError({'media': [f'Identifiant de média invalide sur {key}']}) from None
        nodes.append({'id':key,'type':'story','position':{'x':x, 'y':y},
                      'data':{'kind':data['kind'],'title':localized('title'),'text':localized('text'),
                              'weight':max(1,min(100,weight)), 'options':options, 'media': media_choice}})
    edges=[]
    used_handles=set()
    for item in payload['edges']:
        if not isinstance(item,dict):raise APIValidationError({'edges':['Liaison invalide']})
        a,b=item.get('source'),item.get('target')
        if a not in identifiers or b not in identifiers:
            raise APIValidationError({'edges':['Une liaison pointe hors du graphe']})
        h=item.get('sourceHandle')
        if h is not None and (not isinstance(h,str) or not SLUG.fullmatch(h)):
            raise APIValidationError({'edges':['Identifiant de branche invalide']})
        k=(a,h)
        if k in used_handles:raise APIValidationError({'edges':['Une sortie ne peut avoir deux destinations']})
        used_handles.add(k)
        edges.append({'id':f'e-{len(edges)+1}', 'source':a,'target':b,'sourceHandle':h,
                      'type':'smoothstep'})
    return {'nodes':nodes,'edges':edges}


def relational_graph(story):
    nodes=list(story.noeuds.all().prefetch_related('options'))
    x={n.id:n for n in nodes}
    result=[];edges=[]
    for i,n in enumerate(nodes):
        kind=n.type.lower()
        result.append({'id':n.cle,'type':'story','position':{'x':160+(i%4)*260,'y':40+(i//4)*225},
          'data':{'kind':kind,'title':{'fr':n.titre_fr,'mg':n.titre_mg},
                  'text':{'fr':n.texte_fr,'mg':n.texte_mg},'weight':n.poids or 20,
                  'options':[{'id':o.cle,'label':{'fr':o.label_fr,'mg':o.label_mg},
                    'feedback':{'fr':o.feedback_fr,'mg':o.feedback_mg},'quality':float(o.qualite)}
                    for o in n.options.all()]}})
        if n.noeud_suivant_id and n.noeud_suivant_id in x:
            edges.append({'id':f'edge-{n.cle}','source':n.cle,'sourceHandle':'out','target':x[n.noeud_suivant_id].cle,'type':'smoothstep'})
        for opt in n.options.all():
            if opt.noeud_cible_id in x:
                edges.append({'id':f'edge-{n.cle}-{opt.cle}','source':n.cle,
                              'sourceHandle':opt.cle,'target':x[opt.noeud_cible_id].cle,'type':'smoothstep'})
    return {'nodes':result,'edges':edges}


def apply_graph(story, graph):
    """Après contrôle, transforme le brouillon en objets Django dans UNE transaction.
    Les médias des nœuds conservés sont conservés. Les nœuds supprimés associés à des
    médias sont refusés pour ne jamais effacer involontairement de fichiers."""
    graph=sanitize_graph(graph)
    mapping={n['id']:n for n in graph['nodes']}
    if 'start' not in mapping or len(mapping)<3:
        raise APIValidationError({'graph':['Créer un nœud de départ start et au moins trois nœuds']})
    outbound=defaultdict(list)
    for e in graph['edges']:outbound[e['source']].append(e)
    for key,n in mapping.items():
        d=n['data'];kind=d['kind'];route=outbound.get(key,[])
        if not all((d[k][l].strip() for k in ('title','text') for l in ('fr','mg'))):
            raise APIValidationError({'graph':[f'Titres et textes FR/MG requis : {key}']})
        if kind=='scene' and (len(route)!=1 or route[0].get('sourceHandle') not in (None, 'out')):
            raise APIValidationError({'graph':[f'Scène {key}: exactement une sortie directe']})
        if kind=='ending' and route:raise APIValidationError({'graph':[f'Fin {key}: aucune sortie']})
        if kind=='decision':
            opts=d['options'];handles=[e.get('sourceHandle') for e in route]
            if len(opts) not in (2,3) or any(h is None for h in handles) or sorted(handles)!=sorted([o['id'] for o in opts]):
                raise APIValidationError({'graph':[f'Décision {key}: relier 2 ou 3 options']})
            if any(not all(o[k][l].strip() for k in ('label','feedback') for l in ('fr','mg')) for o in opts):
                raise APIValidationError({'graph':[f'Options FR/MG et retours requis : {key}']})
    # Interdit les cycles, interdit les chemins sans fin et nœuds inatteignables.
    visited=set(); terminal=set(); decisions=[]
    def traverse(k,stack,count):
        if k in stack:raise APIValidationError({'graph':[f'Cycle détecté : {k}']})
        n=mapping[k];visited.add(k);kind=n['data']['kind']
        if kind=='ending':terminal.add(k);decisions.append(count);return
        for e in outbound[k]:traverse(e['target'],stack|{k},count+(kind=='decision'))
    traverse('start',set(),0)
    if len(visited)!=len(mapping) or not terminal:
        raise APIValidationError({'graph':['Nœuds inaccessibles ou sans fin']})
    if any(n > story.decisions_attendues for n in decisions):
        raise APIValidationError({'graph':[f'Chaque parcours doit avoir au maximum {story.decisions_attendues} décisions avant publication']})
    with transaction.atomic():
        old={n.cle:n for n in Noeud.objects.select_for_update().filter(tantara=story)}
        removed=[n for key,n in old.items() if key not in mapping]
        # Un nœud éditorial contenant une vidéo ne doit pas devenir une décision :
        # seuls SCENE et ENDING sont des supports média.
        converted_with_media=[key for key,n in old.items()
                              if key in mapping and mapping[key]['data']['kind']=='decision'
                              and n.scene_media.exists()]
        if converted_with_media:
            raise APIValidationError({'graph':['Retirer les médias avant de transformer un nœud en décision : '+', '.join(converted_with_media)]})
        if any(n.scene_media.exists() for n in removed):
            raise APIValidationError({'graph':['Nœud supprimé associé à un média : retirer/réaffecter le média avant application']})
        # Les options existantes sont reconstruites après les nœuds ; pas de modification
        # de l'identifiant du parent. Les IDs stables des nœuds sont préservés.
        OptionDecision.objects.filter(noeud__tantara=story).delete()
        objects={}
        def upsert(k):
            if k in objects:return objects[k]
            item=mapping[k];d=item['data'];kind=d['kind']
            next_node=upsert(outbound[k][0]['target']) if kind=='scene' else None
            obj=old.get(k) or Noeud(tantara=story,cle=k)
            obj.type=kind.upper();obj.titre_fr=d['title']['fr'];obj.titre_mg=d['title']['mg'];obj.texte_fr=d['text']['fr'];obj.texte_mg=d['text']['mg']
            obj.noeud_suivant=next_node;obj.poids=d['weight'] if kind=='decision' else None
            obj.ordre=list(mapping).index(k)
            obj.full_clean();obj.save();objects[k]=obj
            return obj
        for k in mapping:upsert(k)
        for key,n in mapping.items():
            if n['data']['kind']!='decision':continue
            for i,o in enumerate(n['data']['options']):
                target=next(e['target'] for e in outbound[key] if e.get('sourceHandle')==o['id'])
                opt=OptionDecision(noeud=objects[key],cle=o['id'],label_fr=o['label']['fr'],label_mg=o['label']['mg'],
                   feedback_fr=o['feedback']['fr'],feedback_mg=o['feedback']['mg'],qualite=o['quality'],
                   noeud_cible=objects[target],ordre=i)
                opt.full_clean();opt.save()
        # Appliquer les médias choisis dans l'éditeur visuel : création automatique d'un SceneMedia FR.
        # Pour MG, l'éditeur audio permet ensuite de créer une association/langue distincte.
        from apps.core.models import Langue
        from apps.media_studio.models import MediaAsset, SceneMedia
        lang = Langue.objects.filter(code='fr', actif=True).first()
        if any(n['data'].get('media') for n in mapping.values()) and not lang:
            raise APIValidationError({'media': ['Initialiser la langue française avant d’appliquer les médias']})
        for key, node in mapping.items():
            if node['data']['kind'] not in ('scene', 'ending'):
                continue
            choice = node['data'].get('media')
            if choice is None:
                continue  # ne pas supprimer les liens historiques si aucun choix explicite
            asset = MediaAsset.objects.filter(pk=choice['asset'], type=choice['kind'], droits_confirmes=True).first()
            if not asset:
                raise APIValidationError({'media': [f'Média introuvable, non conforme ou droits non confirmés : {key}']})
            existing = SceneMedia.objects.filter(noeud=objects[key], langue=lang).first()
            new_mode = SceneMedia.Mode.VIDEO_ORIGINAL if choice['kind'] == 'VIDEO' else SceneMedia.Mode.IMAGE_AUDIO
            if existing and (
                    (existing.video_id == asset.pk and new_mode == SceneMedia.Mode.VIDEO_ORIGINAL
                     and existing.mode in (SceneMedia.Mode.VIDEO_ORIGINAL, SceneMedia.Mode.VIDEO_AUDIO)) or
                    (existing.image_id == asset.pk and new_mode == SceneMedia.Mode.IMAGE_AUDIO
                     and existing.mode == SceneMedia.Mode.IMAGE_AUDIO)):
                continue  # conserver les voix/audio et rendus déjà préparés
            if not existing:
                existing = SceneMedia(noeud=objects[key], langue=lang)
            existing.mode = new_mode
            existing.video = asset if choice['kind'] == 'VIDEO' else None
            existing.image = asset if choice['kind'] == 'IMAGE' else None
            existing.audio = None
            existing.video_finale = None
            existing.statut = SceneMedia.Status.DRAFT
            existing.full_clean()
            existing.save()
        for n in removed:n.delete()
        validate_story_graph(story, require_complete=False)
        story.statut_editorial=StatutEditorial.BROUILLON
        story.save(update_fields=['statut_editorial','updated_at'])
    return len(objects)
