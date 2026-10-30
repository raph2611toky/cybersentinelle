"""Validation d'uploads et persistance sécurisée des fichiers du studio."""
import hashlib
import mimetypes
from pathlib import Path
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, UnidentifiedImageError
from .video import probe
from ..models import MediaAsset

EXTENSIONS = {
    'IMAGE': {'.png', '.jpg', '.jpeg', '.webp'},
    'VIDEO': {'.mp4', '.mov', '.webm'},
    'AUDIO': {'.mp3', '.wav', '.m4a', '.ogg'},
    'SUBTITLE': {'.vtt', '.srt'},
}


def inspect_upload(upload, kind):
    suffix = Path(upload.name).suffix.lower()
    if kind not in EXTENSIONS or suffix not in EXTENSIONS[kind]:
        raise ValidationError({'fichier': 'Format non autorisé pour ce type de média.'})
    if upload.size <= 0 or upload.size > settings.STUDIO_MAX_UPLOAD_BYTES:
        raise ValidationError({'fichier': 'Taille du fichier non autorisée.'})
    if kind == 'SUBTITLE':
        if upload.size > 512 * 1024:
            raise ValidationError({'fichier': 'Sous-titres trop volumineux.'})
        try:
            text = upload.read().decode('utf-8-sig')
            if '\x00' in text or not text.strip():
                raise ValueError('bad subtitle')
            if suffix == '.vtt' and not text.lstrip().startswith('WEBVTT'):
                raise ValueError('bad vtt')
        except (UnicodeError, ValueError):
            raise ValidationError({'fichier': 'Sous-titres non valides (UTF-8/VTT).'} ) from None
        finally:
            upload.seek(0)
        return {'mime_type': 'text/vtt' if suffix == '.vtt' else 'application/x-subrip'}
    if kind == 'IMAGE':
        try:
            with Image.open(upload) as img:
                img.verify()
            upload.seek(0)
            with Image.open(upload) as img:
                width, height = img.size
                fmt = img.format
            if fmt not in {'PNG', 'JPEG', 'WEBP'} or width*height > 24_000_000:
                raise ValueError('bad image')
            return {'mime_type': Image.MIME[fmt], 'largeur_px': width, 'hauteur_px': height}
        except (UnidentifiedImageError, ValueError, OSError, Image.DecompressionBombError):
            raise ValidationError({'fichier': 'Image non valide ou trop grande.'}) from None
        finally:
            upload.seek(0)
    # L'inspection FFprobe se fait après enregistrement dans l'espace privé.
    return {'mime_type': mimetypes.guess_type(upload.name)[0] or 'application/octet-stream'}


def persist_upload(upload, kind, title, licence, langue=None, origin='UPLOAD', provider='', rights_confirmed=True):
    if not licence or not licence.strip():
        raise ValidationError({'licence': 'La provenance ou la licence est obligatoire.'})
    props = inspect_upload(upload, kind)
    digest = hashlib.sha256()
    for chunk in upload.chunks():
        digest.update(chunk)
    upload.seek(0)
    asset = MediaAsset(titre=title, type=kind, licence=licence, droits_confirmes=rights_confirmed,
        origine=origin, provider=provider, langue=langue,
        sha256=digest.hexdigest(), taille_octets=upload.size, **props)
    asset.fichier.save(upload.name, upload, save=False)
    try:
        if kind in {'VIDEO', 'AUDIO'}:
            meta = probe(asset.fichier.path)
            streams = meta.get('streams', [])
            if not any(s.get('codec_type') == kind.lower() for s in streams):
                raise ValidationError({'fichier': 'Codec et flux incompatibles avec le type demandé.'})
            duration = float(meta.get('format', {}).get('duration', 0) or 0)
            if duration <= 0 or duration > settings.STUDIO_MAX_MEDIA_SECONDS:
                raise ValidationError({'fichier': 'Durée de média non autorisée.'})
            asset.duree_ms = round(duration * 1000)
            video = next((s for s in streams if s.get('codec_type') == 'video'), None)
            if video:
                asset.largeur_px = int(video.get('width', 0) or 0)
                asset.hauteur_px = int(video.get('height', 0) or 0)
        asset.full_clean()
        asset.save()
        return asset
    except Exception:
        asset.fichier.delete(save=False)
        raise


def persist_generated(data, extension, mimetype, *, title, licence, lang=None, origin='TTS', provider=''):
    if not data or len(data) > settings.STUDIO_MAX_TTS_RESULT_BYTES:
        raise ValidationError('Fichier généré invalide.')
    upload = ContentFile(data, name=f'generated{extension}')
    return persist_upload(upload, 'AUDIO', title, licence, langue=lang, origin=origin, provider=provider, rights_confirmed=False)
