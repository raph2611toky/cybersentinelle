"""Publication contrôlée : seule une release figée sert les endpoints publics."""

import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from helpers.helper import media_url
from django.utils import timezone
from apps.core.models import Langue
from apps.core.choices import (
    StatutEditorial,
    StatutPublication,
    StatutService,
    TypeFichierContenu,
)
from apps.content_api.models import Tantara, Visuel, Sujet
from apps.content_api.validation import validate_story_graph
from apps.content_api.serializers import story_dict
from apps.resources.models import RessourceAide
from apps.resources.serializers import resource_dict
from apps.resources.validation import validate_resource
from apps.pedagogie.models import QuestionPedagogique
from apps.pedagogie.serializers import question_dict
from apps.pedagogie.validation import validate_question
from .models import VersionContenu, FichierContenu


class ReleaseNotFound(Exception):
    pass


def dump_json(obj):
    return (
        json.dumps(obj, sort_keys=True, ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _safe_release_dir(relative):
    root = settings.RELEASES_ROOT.resolve()
    path = (settings.CONTENT_ROOT / relative).resolve()
    if not path.is_relative_to(root) or path == root:
        raise ReleaseNotFound("Répertoire de publication invalide")
    return path


def _read_verified(path, digest):
    if not path.is_file():
        raise ReleaseNotFound("Fichier publié manquant")
    data = path.read_bytes()
    if sha(data) != digest:
        raise ReleaseNotFound("Intégrité du contenu invalide")
    return json.loads(data)


def active_release():
    version = VersionContenu.objects.filter(statut=StatutPublication.ACTIVE).first()
    if version is None:
        raise ReleaseNotFound("Aucune publication active")
    root = _safe_release_dir(version.repertoire_snapshot)
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise ReleaseNotFound("Manifest absent")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        manifest.get("sha256") != version.digest_global
        or manifest.get("version") != version.numero
    ):
        raise ReleaseNotFound("Manifest incohérent")
    entries = manifest.get("files", [])
    canonical = "\n".join(
        f"{entry['path']}:{entry['sha256']}"
        for entry in sorted(entries, key=lambda f: f["path"])
    )
    if sha(canonical.encode("utf-8")) != version.digest_global:
        raise ReleaseNotFound("Empreinte manifest incorrecte")
    return root, manifest


def read_content(relative_path):
    root, manifest = active_release()
    entry = next((f for f in manifest["files"] if f["path"] == relative_path), None)
    if not entry:
        raise ReleaseNotFound("Contenu non trouvé")
    path = (root / relative_path).resolve()
    if not path.is_relative_to(root):
        raise ReleaseNotFound("Chemin invalide")
    return _read_verified(path, entry["sha256"]), manifest


def decorate_story_urls(data, manifest, request):
    """Les *_url sont absolues et correspondent exclusivement aux assets déclarés."""
    assets = manifest.get("assets", {})
    visual = data.get("heroVisual")
    if visual and visual in assets:
        data["heroVisual_url"] = media_url(assets[visual], request)
    for node in data.get("nodes", {}).values():
        v = node.get("visual")
        if v and v in assets:
            node["visual_url"] = media_url(assets[v], request)
    return data


def manifest_public(manifest):
    return {k: manifest[k] for k in ("version", "date", "languages", "sha256", "files")}


def publication_payload():
    """Prépare et valide sans mutation de la base : histoires approuvées et graphes vérifiés."""
    languages = set(Langue.objects.filter(actif=True).values_list("code", flat=True))
    if not {"fr", "mg"}.issubset(languages):
        raise ValidationError("Langues fr et mg actives obligatoires")
    stories = list(
        Tantara.objects.select_related("visuel_heros")
        .prefetch_related("noeuds__options__noeud_cible", "noeuds__visuel")
        .filter(statut_editorial__in=[StatutEditorial.APPROUVE, StatutEditorial.PUBLIE])
    )
    if not stories:
        raise ValidationError("Au moins une histoire est requise pour publier")
    assets = {}
    for visual in Visuel.objects.filter(actif=True):
        visual.full_clean()
        # Les chemins statiques doivent référencer une ressource intégrée au dépôt.
        asset_path = visual.fichier.name or visual.chemin_asset
        p = (settings.MEDIA_ROOT / asset_path).resolve()
        if not p.is_relative_to(settings.MEDIA_ROOT.resolve()):
            raise ValidationError("Chemin de média invalide")
        if not p.is_file():
            raise ValidationError(f"Asset absent : {visual.code}")
        if visual.sha256 and sha(p.read_bytes()) != visual.sha256:
            raise ValidationError(f"Asset modifié : {visual.code}")
        if visual.licence.strip().lower() in {"a-documenter", "unknown", "inconnue"}:
            raise ValidationError(f"Licence à vérifier : {visual.code}")
        assets[visual.code] = asset_path
    result = {}
    for story in stories:
        story.full_clean()
        if story.statut_editorial not in {
            StatutEditorial.APPROUVE,
            StatutEditorial.PUBLIE,
        }:
            raise ValidationError(f"{story.slug}: validation éditoriale absente")
        for x in (
            story.relecture_fr_le,
            story.relecture_mg_le,
            story.relecteur_fr_role.strip(),
            story.relecteur_mg_role.strip(),
        ):
            if not x:
                raise ValidationError(
                    f"{story.slug}: relectures bilingues obligatoires"
                )
        if not story.visuel_heros_id or story.visuel_heros.code not in assets:
            raise ValidationError(f"{story.slug}: visuel héros absent")
        for node in story.noeuds.all():
            node.full_clean()
            if node.visuel_id and node.visuel.code not in assets:
                raise ValidationError(f"{story.slug}: visuel de scène absent")
            for option in node.options.all():
                option.full_clean()
        validate_story_graph(story)
        result[f"stories/{story.slug}.json"] = story_dict(story, None, True)
    for sujet in Sujet.objects.filter(actif=True):
        sujet.full_clean()
    resources = list(
        RessourceAide.objects.select_related("source", "ressource_repli").filter(
            statut_editorial__in=[StatutEditorial.APPROUVE, StatutEditorial.PUBLIE]
        )
    )
    included_ids = {r.pk for r in resources}
    for r in resources:
        if r.ressource_repli_id and r.ressource_repli_id not in included_ids:
            raise ValidationError(f"{r.cle}: ressource de repli non publiable")
        r.source.full_clean()
        validate_resource(r)
        for x in (
            r.relecture_fr_le,
            r.relecture_mg_le,
            r.relecteur_fr_role.strip(),
            r.relecteur_mg_role.strip(),
        ):
            if not x:
                raise ValidationError(f"{r.cle}: relecture requise")
    result["resources.json"] = [resource_dict(r) for r in resources]
    questions = list(
        QuestionPedagogique.objects.select_related("sujet").filter(
            statut_editorial__in=[StatutEditorial.APPROUVE, StatutEditorial.PUBLIE]
        )
    )
    for q in questions:
        validate_question(q)
        for x in (
            q.relecture_fr_le,
            q.relecture_mg_le,
            q.relecteur_fr_role.strip(),
            q.relecteur_mg_role.strip(),
        ):
            if not x:
                raise ValidationError(f"{q.cle}: relecture requise")
        for linked in q.ressources_liees.all():
            if linked not in resources:
                raise ValidationError(f"{q.cle}: ressource liée non publiée")
    result["questions.json"] = [question_dict(q) for q in questions]
    return result, assets


def publish(numero, journal=""):
    """Génère une release atomique, et bascule la version active en transaction."""
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,39}", numero):
        raise ValidationError("Numéro de version invalide")
    if VersionContenu.objects.filter(numero=numero).exists():
        raise ValidationError("Numéro de publication déjà existant")
    payload, assets = publication_payload()
    settings.RELEASES_ROOT.mkdir(parents=True, exist_ok=True)
    final = settings.RELEASES_ROOT / numero
    if final.exists():
        raise ValidationError("Répertoire de publication existe déjà")
    staging = Path(tempfile.mkdtemp(prefix=".staging-", dir=settings.RELEASES_ROOT))
    finished = False
    try:
        entries = []
        for path, value in sorted(payload.items()):
            raw = dump_json(value)
            file = staging / path
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(raw)
            typ = (
                "STORY"
                if path.startswith("stories/")
                else ("RESOURCES" if path.startswith("resources") else "QUESTIONS")
            )
            entries.append(
                {
                    "path": path,
                    "type": typ,
                    "sha256": sha(raw),
                    "bytes": len(raw),
                    "language": None,
                }
            )
        canonical = "\n".join(
            f"{e['path']}:{e['sha256']}"
            for e in sorted(entries, key=lambda e: e["path"])
        )
        digest = sha(canonical.encode("utf-8"))
        now = timezone.now()
        manifest = {
            "version": numero,
            "date": now.isoformat(),
            "languages": ["fr", "mg"],
            "sha256": digest,
            "files": entries,
            "assets": assets,
        }
        (staging / "manifest.json").write_bytes(dump_json(manifest))
        staging.replace(final)
        finished = True
        with transaction.atomic():
            VersionContenu.objects.filter(statut=StatutPublication.ACTIVE).update(
                statut=StatutPublication.ARCHIVEE, active_slot=None
            )
            version = VersionContenu.objects.create(
                numero=numero,
                statut=StatutPublication.ACTIVE,
                date_publication=now,
                digest_global=digest,
                repertoire_snapshot=f"releases/{numero}",
                journal=journal,
            )
            version.langues.set(
                Langue.objects.filter(code__in=["fr", "mg"], actif=True)
            )
            for i, e in enumerate(entries):
                FichierContenu.objects.create(
                    version=version,
                    chemin=e["path"],
                    type=e["type"],
                    sha256=e["sha256"],
                    taille_octets=e["bytes"],
                    ordre=i,
                )
        return version
    except Exception:
        if finished:
            shutil.rmtree(final, ignore_errors=True)
        raise
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)


def rollback(numero):
    with transaction.atomic():
        version = VersionContenu.objects.select_for_update().get(numero=numero)
        root = _safe_release_dir(version.repertoire_snapshot)
        manifest = json.loads((root / "manifest.json").read_text("utf-8"))
        if (
            manifest.get("sha256") != version.digest_global
            or manifest.get("version") != version.numero
        ):
            raise ValidationError("Manifest du rollback invalide")
        canonical = "\n".join(
            f"{e['path']}:{e['sha256']}"
            for e in sorted(manifest["files"], key=lambda e: e["path"])
        )
        if sha(canonical.encode("utf-8")) != version.digest_global:
            raise ValidationError("Inventaire du rollback corrompu")
        for e in manifest["files"]:
            p = (root / e["path"]).resolve()
            if not p.is_relative_to(root):
                raise ValidationError("Chemin dans le manifest invalide")
            _read_verified(p, e["sha256"])
        VersionContenu.objects.filter(statut=StatutPublication.ACTIVE).exclude(
            pk=version.pk
        ).update(statut=StatutPublication.ARCHIVEE, active_slot=None)
        version.statut = StatutPublication.ACTIVE
        version.save(update_fields=["statut", "active_slot", "updated_at"])
        return version
