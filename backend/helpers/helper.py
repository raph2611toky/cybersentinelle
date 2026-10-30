from datetime import datetime
from django.core.files.storage import default_storage
from django.conf import settings
from django.utils import timezone


def time_elapsed(value: datetime, now: datetime | None = None) -> int:
    """Nombre de secondes écoulées, jamais négatif, dates avec fuseau requis."""
    now = now or timezone.now()
    if timezone.is_naive(value) or timezone.is_naive(now):
        raise ValueError("Une date avec fuseau horaire est requise.")
    return max(0, int((now - value).total_seconds()))


def media_url(path, request=None):
    """URL de stockage, pas d'assemblage naïf de MEDIA_URL et du chemin."""
    if not path:
        return None
    url = default_storage.url(str(path).lstrip("/"))
    return request.build_absolute_uri(url) if request else url


def normalize_image(upload):
    """Valide et réencode un média éditorial en PNG sans métadonnées d'origine."""
    import uuid
    from io import BytesIO
    from django.core.exceptions import ValidationError
    from django.core.files.base import ContentFile
    from PIL import Image, UnidentifiedImageError

    if upload.size > 5 * 1024 * 1024:
        raise ValidationError("Image limitée à 5 Mo.")
    try:
        upload.seek(0)
        with Image.open(upload) as image:
            if image.format not in {"PNG", "JPEG", "WEBP"}:
                raise ValidationError("Formats autorisés : PNG, JPEG, WEBP.")
            if image.width * image.height > 20000000:
                raise ValidationError("Image limitée à 20 millions de pixels.")
            converted = image.convert("RGBA")
            clean = Image.new("RGBA", converted.size)
            clean.paste(converted)
            output = BytesIO()
            clean.save(output, format="PNG")
            result = ContentFile(output.getvalue(), name=f"{uuid.uuid4().hex}.png")
            result.image_dimensions = image.size
            return result
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValidationError("Image invalide ou trop volumineuse.") from exc
