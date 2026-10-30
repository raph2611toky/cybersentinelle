"""Les scènes peuvent précéder d'autres décisions ; les fins acceptent un média.
Tests unitaires sans appels réseaux et sans worker Celery.
"""
import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from apps.core.models import Langue
from apps.content_api.graph_service import apply_graph
from apps.content_api.models import Noeud
from apps.media_studio.serializers import SceneSerializer
from apps.media_studio.models import SceneMedia
from django.core.exceptions import ValidationError as DjangoValidationError
from tests.test_dashboard_integration import _story, _graph

pytestmark = pytest.mark.django_db


def test_decision_scene_decision_ending_is_a_valid_path():
    story = _story()
    story.decisions_attendues = 2
    story.save(update_fields=['decisions_attendues'])
    graph = _graph()
    nodes = {n['id']: n for n in graph['nodes']}
    first = nodes['decision-1']
    first['data']['options'][0]['label'] = {'fr': 'Aider', 'mg': 'Manampy'}
    first['data']['options'][1]['label'] = {'fr': 'Attendre', 'mg': 'Miandry'}
    new_scene_a = {'id': 'scene-a', 'position': {'x': 10, 'y': 360},
                   'data': {'kind':'scene', 'title':{'fr':'Une aide', 'mg':'Fanampiana'},
                            'text':{'fr':'La personne intervient.', 'mg':'Miditra an-tsehatra izy.'}}}
    new_scene_b = {'id': 'scene-b', 'position': {'x': 360, 'y': 360},
                   'data': {'kind':'scene', 'title':{'fr':'Un doute', 'mg':'Fisalasalanana'},
                            'text':{'fr':'La personne attend.', 'mg':'Miandry izy.'}}}
    new_decision = {'id': 'decision-2', 'position': {'x': 200, 'y': 530},
                    'data': {'kind': 'decision', 'title': {'fr':'Demander soutien','mg':'Mangataka fanohanana'},
                             'text': {'fr':'Que faire ensuite ?','mg':'Inona indray no hatao?'},
                             'weight': 20,
                             'options': first['data']['options']}}
    # Une seconde décision a ses propres clés et peut mener aux mêmes fins.
    new_decision['data']['options'] = [dict(o, id='next-'+o['id']) for o in first['data']['options']]
    graph['nodes'] += [new_scene_a, new_scene_b, new_decision]
    graph['edges'] = [
        {'source':'start', 'sourceHandle':'out', 'target':'decision-1'},
        {'source':'decision-1', 'sourceHandle':'opt-a', 'target':'scene-a'},
        {'source':'decision-1', 'sourceHandle':'opt-b', 'target':'scene-b'},
        {'source':'scene-a', 'sourceHandle':'out', 'target':'decision-2'},
        {'source':'scene-b', 'sourceHandle':'out', 'target':'decision-2'},
        {'source':'decision-2', 'sourceHandle':'next-opt-a', 'target':'ending-a'},
        {'source':'decision-2', 'sourceHandle':'next-opt-b', 'target':'ending-b'},
    ]
    assert apply_graph(story, graph) == 7
    assert Noeud.objects.get(tantara=story, cle='scene-a').noeud_suivant.cle == 'decision-2'
    assert Noeud.objects.filter(tantara=story, type='ENDING').count() == 2


def test_graph_read_exposes_persisted_node_ids():
    user=get_user_model().objects.create_superuser('graph_admin',password='StrongPassword123!')
    story=_story()
    apply_graph(story, _graph())
    client=Client()
    client.force_login(user)
    response=client.get(f'/api/editor/stories/{story.pk}/graph/')
    assert response.status_code == 200
    assert response.json()['node_id_map']['start'] == str(Noeud.objects.get(tantara=story, cle='start').pk)


def test_scene_and_ending_are_valid_media_targets_but_decision_is_not():
    story = _story()
    apply_graph(story, _graph())
    lang,_=Langue.objects.get_or_create(code='fr', defaults={'nom_fr':'Français', 'nom_mg':'Frantsay', 'nom_natif':'Français'})
    for key in ('start', 'ending-a'):
        node=Noeud.objects.get(tantara=story, cle=key)
        serializer=SceneSerializer(data={'noeud':str(node.pk),'langue':str(lang.pk),'mode':'TEXT_ONLY'})
        assert serializer.is_valid(), serializer.errors
    decision=Noeud.objects.get(tantara=story, cle='decision-1')
    serializer=SceneSerializer(data={'noeud':str(decision.pk),'langue':str(lang.pk),'mode':'TEXT_ONLY'})
    assert not serializer.is_valid()
    assert 'noeud' in serializer.errors
    with pytest.raises(DjangoValidationError):
        SceneMedia(noeud=decision, langue=lang, mode='TEXT_ONLY').full_clean()
