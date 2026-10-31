"""Ne sert que les fichiers présents dans un manifeste de publication vérifié."""
import hashlib
import re
from pathlib import Path
from django.conf import settings
from django.http import FileResponse, StreamingHttpResponse, HttpResponse
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from helpers.api.responses import error, failed
from apps.publication.models import VersionContenu
from apps.publication.services import _safe_release_dir, _read_verified, sha
from .public_swagger import public_media_doc, public_subtitle_doc


class PublishedSceneMediaAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @public_media_doc
    def get(self, request, version, asset_id):
        try:
            if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9._-]{0,39}', version):
                return error(404, 'NOT_FOUND', 'Clip introuvable')
            release = VersionContenu.objects.filter(numero=version).first()
            if not release:
                return error(404, 'NOT_FOUND', 'Clip introuvable')
            root = _safe_release_dir(release.repertoire_snapshot)
            manifest_file = root / 'manifest.json'
            import json
            manifest = json.loads(manifest_file.read_text(encoding='utf-8'))
            entries = manifest.get('files', [])
            canonical = '\n'.join(f"{e['path']}:{e['sha256']}" for e in sorted(entries, key=lambda e: e['path']))
            if manifest.get('version') != release.numero or sha(canonical.encode()) != release.digest_global:
                return error(503, 'CONTENT_NOT_PUBLISHED', 'Publication invalide')
            allowed = (f'media/{asset_id}.mp4', f'media/{asset_id}.mp3')
            entry = next((e for e in entries if e.get('path') in allowed and e.get('type') == 'MEDIA'), None)
            target = entry['path'] if entry else None
            if not entry:
                return error(404, 'NOT_FOUND', 'Clip introuvable')
            fpath = (root / target).resolve()
            if not fpath.is_relative_to(root) or not fpath.is_file():
                return error(404, 'NOT_FOUND', 'Clip introuvable')
            digest = hashlib.sha256()
            with fpath.open('rb') as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(chunk)
            if digest.hexdigest() != entry['sha256']:
                return error(503, 'CONTENT_NOT_PUBLISHED', 'Média publié corrompu')
            mime = 'audio/mpeg' if target.endswith('.mp3') else 'video/mp4'
            from .views import parse_byte_range, stream_range
            size = fpath.stat().st_size
            range_header = request.headers.get('Range')
            if range_header:
                byte_range = parse_byte_range(range_header, size)
                if byte_range is None:
                    response = HttpResponse(status=416)
                    response['Content-Range'] = f'bytes */{size}'
                    return response
                start, end = byte_range
                response = StreamingHttpResponse(stream_range(fpath.open('rb'), start, end-start+1), status=206, content_type=mime)
                response['Content-Range'] = f'bytes {start}-{end}/{size}'
                response['Content-Length'] = str(end-start+1)
            else:
                response = FileResponse(fpath.open('rb'), content_type=mime)
            response['Accept-Ranges'] = 'bytes' 
            response['Content-Disposition'] = f'inline; filename="clip-{asset_id}.{target.rsplit('.', 1)[-1]}"'
            response['Cache-Control'] = 'public, max-age=86400, immutable'
            return response
        except Exception as exc:
            return failed(exc)


class PublishedSceneSubtitleAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @public_subtitle_doc
    def get(self, request, version, asset_id, ext):
        try:
            if ext not in {'vtt', 'srt'} or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9._-]{0,39}', version):
                return error(404, 'NOT_FOUND', 'Sous-titres introuvables')
            release = VersionContenu.objects.filter(numero=version).first()
            if not release:
                return error(404, 'NOT_FOUND', 'Sous-titres introuvables')
            root = _safe_release_dir(release.repertoire_snapshot)
            import json
            manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
            entries = manifest.get('files', [])
            canonical = '\n'.join(f"{e['path']}:{e['sha256']}" for e in sorted(entries, key=lambda e: e['path']))
            if manifest.get('version') != release.numero or sha(canonical.encode()) != release.digest_global:
                return error(503, 'CONTENT_NOT_PUBLISHED', 'Publication invalide')
            target = f'subtitles/{asset_id}.{ext}'
            entry = next((e for e in entries if e.get('path') == target and e.get('type') == 'MEDIA'), None)
            if not entry:
                return error(404, 'NOT_FOUND', 'Sous-titres introuvables')
            filepath = (root / target).resolve()
            if not filepath.is_relative_to(root) or not filepath.is_file():
                return error(404, 'NOT_FOUND', 'Sous-titres introuvables')
            digest = hashlib.sha256()
            with filepath.open('rb') as fh:
                for chunk in iter(lambda: fh.read(1024 * 1024), b''):
                    digest.update(chunk)
            if digest.hexdigest() != entry['sha256']:
                return error(503, 'CONTENT_NOT_PUBLISHED', 'Sous-titres corrompus')
            resp = FileResponse(filepath.open('rb'), content_type='text/vtt' if ext == 'vtt' else 'application/x-subrip')
            resp['Cache-Control'] = 'public, max-age=86400, immutable'
            resp['Content-Disposition'] = f'inline; filename="subtitle-{asset_id}.{ext}"'
            return resp
        except Exception as exc:
            return failed(exc)
