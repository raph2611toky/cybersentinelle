import re
from pathlib import PurePosixPath
from django.core.exceptions import ValidationError


def bilingual(a, b, name="Texte"):
    if not a or not a.strip() or not b or not b.strip():
        raise ValidationError(f"{name}: versions FR et MG obligatoires")


def sha256_validator(value):
    if not re.fullmatch(r"[0-9a-f]{64}", value or ""):
        raise ValidationError(
            "SHA-256 doit contenir 64 caractères hexadécimaux minuscules"
        )


def relative_asset(value):
    if not value or chr(92) in value or value.startswith("/") or value.startswith("~"):
        raise ValidationError("Chemin relatif invalide")
    if ".." in PurePosixPath(value).parts or PurePosixPath(value).is_absolute():
        raise ValidationError("Traversée de répertoire interdite")
    if ":" in value.split("/")[0] or "?" in value or "#" in value:
        raise ValidationError("Chemin statique invalide")


def https_or_tel(value):
    if not (value.startswith("https://") or re.fullmatch(r"tel:\+?[0-9]{2,16}", value)):
        raise ValidationError("Seuls les liens HTTPS ou tel: sont acceptés")
