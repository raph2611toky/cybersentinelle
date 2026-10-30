"""Contrats d'intégration du studio SAFIDIKO : cookie staff, CSRF, graphe."""
import pytest
from django.contrib.auth.models import User
from django.test import Client
from apps.content_api.models import Tantara, Noeud, BrouillonGraphe

pytestmark = pytest.mark.django_db


def _story():
    return Tantara.objects.create(
        slug='test-studio', numero='89', titre_fr='Test', titre_mg='Fitsapana',
        sous_titre_fr='Histoire fictive', sous_titre_mg='Tantara noforonina',
        theme_fr='Protection', theme_mg='Fiarovana',
        description_fr='Fiction pédagogique', description_mg='Famoronana fianarana',
        avertissement_fr='Contenu fictif', avertissement_mg='Tantara noforonina',
        duree='4 min', decisions_attendues=1, palette='default',
    )


def _graph():
    def tr(a,b): return {'fr': a, 'mg': b}
    return {
        'nodes':[
            {'id':'start','position':{'x':0,'y':0},'data':{'kind':'scene','title':tr('Début','Fiandohana'),'text':tr('Texte de départ','Lahatsoratra fiandohana')}},
            {'id':'decision-1','position':{'x':0,'y':180},'data':{'kind':'decision','title':tr('Choisir','Mifidy'),'text':tr('Que faire ?','Inona no atao?'),'weight':20,'options':[
               {'id':'opt-a','label':tr('Demander de l’aide','Mangataka fanampiana'),'feedback':tr('Bonne approche','Tsara izany'),'quality':1},
               {'id':'opt-b','label':tr('Attendre','Miandry'),'feedback':tr('Chercher du soutien','Mitady fanohanana'),'quality':0},
            ]}},
            {'id':'ending-a','position':{'x':-150,'y':330},'data':{'kind':'ending','title':tr('Fin A','Famaranana A'),'text':tr('Aide obtenue','Nahazo fanampiana')}},
            {'id':'ending-b','position':{'x':150,'y':330},'data':{'kind':'ending','title':tr('Fin B','Famaranana B'),'text':tr('Une autre issue','Vokatra hafa')}},
        ],
        'edges':[
          {'source':'start','sourceHandle':'out','target':'decision-1'},
          {'source':'decision-1','sourceHandle':'opt-a','target':'ending-a'},
          {'source':'decision-1','sourceHandle':'opt-b','target':'ending-b'},
        ],
    }


def test_csrf_cookie_staff_login_session_and_logout():
    User.objects.create_superuser('operator',password='Strong-pass-3422!')
    client=Client(enforce_csrf_checks=True)
    csrf=client.get('/api/editor/auth/csrf/')
    assert csrf.status_code==200
    assert 'csrftoken' in client.cookies
    assert client.post('/api/editor/auth/login/',data='{"username":"operator","password":"Strong-pass-3422!"}',content_type='application/json').status_code==403
    headers={'HTTP_X_CSRFTOKEN':client.cookies['csrftoken'].value}
    logged=client.post('/api/editor/auth/login/',data='{"username":"operator","password":"Strong-pass-3422!"}',content_type='application/json',**headers)
    assert logged.status_code==200,logged.content
    assert client.cookies['sessionid']['httponly']
    assert client.get('/api/editor/auth/me/').status_code==200
    headers={'HTTP_X_CSRFTOKEN':client.cookies['csrftoken'].value}
    assert client.post('/api/editor/auth/logout/',data='{}',content_type='application/json',**headers).status_code==200
    assert client.get('/api/editor/auth/me/').status_code in (401,403)


def test_staff_login_rejects_regular_user():
    User.objects.create_user('student',password='Other-pass-272!')
    client=Client(enforce_csrf_checks=True)
    client.get('/api/editor/auth/csrf/')
    response=client.post('/api/editor/auth/login/',data='{"username":"student","password":"Other-pass-272!"}',content_type='application/json',HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value)
    assert response.status_code==401
    assert 'sessionid' not in client.cookies


def test_graph_save_revision_conflict_then_apply():
    User.objects.create_superuser('operator', password='Strong-pass-3422!')
    story=_story()
    client=Client()
    client.login(username='operator',password='Strong-pass-3422!')
    base=f'/api/editor/stories/{story.id}/graph/'
    initial=client.get(base)
    assert initial.status_code==200
    assert initial.json()['revision']==0
    import json
    payload={'graph':_graph(),'revision':0}
    saved=client.put(base+'save/',data=json.dumps(payload),content_type='application/json')
    assert saved.status_code==200,saved.content
    assert saved.json()['revision']==1
    assert client.put(base+'save/',data=json.dumps(payload),content_type='application/json').status_code==409
    applied=client.post(base+'apply/',data='{}',content_type='application/json')
    assert applied.status_code==200,applied.content
    assert applied.json()['nodes']==4
    assert Noeud.objects.filter(tantara=story).count()==4
    assert BrouillonGraphe.objects.filter(tantara=story).exists()
