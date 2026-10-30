"""Garde-fous des conventions obligatoires de l'API SAFIDIKO."""
import inspect
import pytest
from django.urls import get_resolver, URLPattern, URLResolver
from rest_framework.views import APIView


def _routes(patterns):
    for entry in patterns:
        if isinstance(entry, URLResolver):
            yield from _routes(entry.url_patterns)
        elif isinstance(entry, URLPattern):
            yield entry


def test_every_api_view_has_one_http_method_and_swagger():
    count = 0
    for url in _routes(get_resolver().url_patterns):
        cls = getattr(url.callback, 'cls', None)
        if cls is None or not issubclass(cls, APIView):
            continue
        count += 1
        assert APIView in cls.__mro__, cls.__name__
        declared = [name for name in ('get', 'post', 'put', 'patch', 'delete')
                    if name in cls.__dict__]
        assert len(declared) == 1, (cls.__name__, declared)
        method = cls.__dict__[declared[0]]
        assert getattr(method, '_swagger_auto_schema', None), cls.__name__
        source = inspect.getsource(method)
        assert 'except Exception' in source, cls.__name__
    assert count == 64


@pytest.mark.django_db
def test_crud_delete_has_explicit_json_response(admin_client):
    from apps.content_api.models import Sujet
    obj = Sujet.objects.create(code='prudence', libelle_fr='Prudence', libelle_mg='Fitandremana')
    res = admin_client.delete(f'/api/editor/topics/{obj.pk}/delete/')
    assert res.status_code == 200
    assert res.json() == {'deleted': True}


def test_manual_multipart_schema_for_visuals(admin_client):
    schema = admin_client.get('/api/swagger.json').json()
    operation = schema['paths']['/editor/visuals/create/']['post']
    assert any(p['in'] == 'formData' and p['name'] == 'fichier'
               and p['type'] == 'file' for p in operation['parameters'])
    assert '201' in operation['responses']
    assert '400' in operation['responses']
    assert '403' in operation['responses']
    assert '500' in operation['responses']
    assert '204' not in operation['responses']
