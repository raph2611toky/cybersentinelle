"""Tests sans appel réseau aux fournisseurs ou à Redis."""
import io
import pytest
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APIClient
from apps.core.models import Langue
from apps.media_studio.models import MediaAsset, VoiceProfile


@pytest.fixture
def staff(db):
    return get_user_model().objects.create_superuser(username='editor_studio', password='SafePassword123!')


@pytest.fixture
def api(staff):
    c = APIClient()
    c.force_authenticate(user=staff)
    return c


@pytest.mark.django_db
def test_private_media_requires_auth():
    c = APIClient()
    response = c.get(reverse('studio-media-list'))
    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_list_schema_contract(api):
    r = api.get(reverse('studio-media-list'))
    assert r.status_code == 200 and r.json() == {'results': []}


@pytest.mark.django_db
def test_file_upload_rejects_executable(api):
    f = SimpleUploadedFile('evil.exe', b'MZ' + b'x' * 80, content_type='application/octet-stream')
    response = api.post(reverse('studio-media-upload'), {
        'titre': 'Fichier interdit', 'type': 'VIDEO', 'licence': 'original',
        'droits_confirmes': 'true', 'fichier': f,
    }, format='multipart')
    assert response.status_code == 400
    assert response.json()['error']['code'] == 'BAD_REQUEST'
    assert not MediaAsset.objects.exists()


@pytest.mark.django_db
def test_voice_profile_create(api):
    fr = Langue.objects.create(code='fr', nom_fr='Français', nom_mg='Frantsay', nom_natif='Français', par_defaut=True)
    r = api.post(reverse('studio-voices-create'), {
        'nom': 'Narrateur FR', 'langue': str(fr.id), 'provider': 'GEMINI',
        'model_id': 'gemini-3.8-flash-lite-tts', 'voice_id': 'Kore', 'actif': True,
    }, format='json')
    assert r.status_code == 201
    assert VoiceProfile.objects.count() == 1


@pytest.mark.django_db
def test_media_download_404_is_json(api):
    import uuid
    resp = api.get(reverse('studio-media-download', kwargs={'pk': uuid.uuid4()}))
    assert resp.status_code == 404
    assert resp.json()['error']['code'] == 'NOT_FOUND'


def test_each_studio_business_view_one_method_and_catches_general_exceptions():
    import ast
    from pathlib import Path
    tree = ast.parse((Path(__file__).parents[1] / 'apps/media_studio/views.py').read_text(encoding='utf-8'))
    methods = {'get', 'post', 'put', 'patch', 'delete'}
    classes = [item for item in tree.body if isinstance(item, ast.ClassDef)]
    assert classes
    for cls in classes:
        verb_methods = [item for item in cls.body if isinstance(item, ast.FunctionDef) and item.name in methods]
        assert len(verb_methods) == 1, cls.name
        assert any(isinstance(x, ast.ExceptHandler) and isinstance(x.type, ast.Name)
                   and x.type.id == 'Exception' for x in ast.walk(verb_methods[0])), cls.name
