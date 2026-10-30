"""Import des vrais JSON V14, sans approbation automatique."""

import json
from pathlib import Path
from decimal import Decimal
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from apps.core.models import Langue
from apps.core.choices import TypeNoeud, StatutEditorial
from apps.content_api.models import Tantara, Noeud, OptionDecision, Visuel, Sujet
from apps.resources.models import Source, RessourceAide
from apps.pedagogie.models import QuestionPedagogique


def tr(obj, key, required=True):
    pair = obj.get(key, {})
    if not isinstance(pair, dict):
        raise ValueError(f"{key} doit être un objet fr/mg")
    fr, mg = pair.get("fr", ""), pair.get("mg", "")
    if required and (
        not isinstance(fr, str)
        or not fr.strip()
        or not isinstance(mg, str)
        or not mg.strip()
    ):
        raise ValueError(f"{key}: contenu FR/MG manquant")
    return {key + "_fr": fr, key + "_mg": mg}


def read_json(path):
    p = Path(path)
    if not p.is_file():
        raise ValueError(f"Fichier absent : {p}")
    return json.loads(p.read_text(encoding="utf-8"))


class Command(BaseCommand):
    help = "Importe les 3 vrais récits V14, optionnellement des référentiels éditoriaux JSON. Aucun contenu n’est approuvé automatiquement."

    def add_arguments(self, parser):
        parser.add_argument("--stories-dir", required=True)
        parser.add_argument(
            "--catalog-dir",
            help="Répertoire contenant visuals.json, sources.json, resources.json, questions.json, subjects.json",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Supprime les anciens brouillons de Tantara avant import",
        )

    def handle(self, *args, **options):
        root = Path(options["stories_dir"])
        try:
            with transaction.atomic():
                for code, fr, mg, natif, default, i in [
                    ("fr", "Français", "Frantsay", "Français", True, 0),
                    ("mg", "Malgache", "Malagasy", "Malagasy", False, 1),
                ]:
                    Langue.objects.update_or_create(
                        code=code,
                        defaults={
                            "nom_fr": fr,
                            "nom_mg": mg,
                            "nom_natif": natif,
                            "par_defaut": default,
                            "actif": True,
                            "ordre": i,
                        },
                    )
                catalog = (
                    Path(options["catalog_dir"]) if options["catalog_dir"] else None
                )
                if catalog:
                    self._catalog(catalog)
                slugs = [
                    ("aza-zaraina", "01", 4),
                    ("tsy-irery", "02", 2),
                    ("aza-manaiky", "03", 2),
                ]
                all_data = []
                for slug, number, decisions in slugs:
                    obj = read_json(root / f"{slug}.json")
                    if obj.get("id") != slug or str(obj.get("number")) != number:
                        raise ValueError(f"{slug}: id/number incompatible V14")
                    if obj.get("expectedDecisions") != decisions:
                        raise ValueError(f"{slug}: expectedDecisions invalide")
                    if "start" not in obj.get("nodes", {}):
                        raise ValueError(f"{slug}: nodes.start absent")
                    unknown = set(obj) - {
                        "id",
                        "number",
                        "title",
                        "subtitle",
                        "theme",
                        "description",
                        "warning",
                        "duration",
                        "expectedDecisions",
                        "palette",
                        "heroVisual",
                        "nodes",
                    }
                    if unknown:
                        raise ValueError(
                            f"{slug}: champs non mappés {sorted(unknown)} ; adapter le contrat avant import"
                        )
                    for key, node in obj["nodes"].items():
                        kind = node.get("kind", "").upper()
                        fields = {
                            "SCENE": {"kind", "title", "text", "tag", "visual", "next"},
                            "DECISION": {"kind", "title", "text", "weight", "options"},
                            "ENDING": {"kind", "title", "text"},
                        }.get(kind, set())
                        unexpected = set(node) - fields
                        if unexpected:
                            raise ValueError(
                                f"{slug}:{key}: champs non mappés {sorted(unexpected)}"
                            )
                        for opt in node.get("options", []):
                            extra = set(opt) - {
                                "id",
                                "label",
                                "feedback",
                                "quality",
                                "next",
                            }
                            if extra:
                                raise ValueError(
                                    f"{slug}:{key}: options non mappées {sorted(extra)}"
                                )
                    all_data.append((obj, slug, number, decisions))
                if options["replace"]:
                    if Tantara.objects.exclude(
                        statut_editorial=StatutEditorial.BROUILLON
                    ).exists():
                        raise ValueError(
                            "Refus de remplacer un contenu déjà validé/publié"
                        )
                    Tantara.objects.all().delete()
                if Tantara.objects.exists():
                    raise ValueError(
                        "Des Tantara existent déjà : utiliser --replace uniquement sur brouillons"
                    )
                for obj, slug, number, decisions in all_data:
                    v = Visuel.objects.filter(code=obj.get("heroVisual", "")).first()
                    s = Tantara.objects.create(
                        slug=slug,
                        numero=number,
                        decisions_attendues=decisions,
                        duree=obj.get("duration", ""),
                        palette=obj.get("palette", ""),
                        visuel_heros=v,
                        ordre=int(number),
                        statut_editorial=StatutEditorial.BROUILLON,
                        **tr(obj, "title"),
                        **tr(obj, "subtitle"),
                        **tr(obj, "theme"),
                        **tr(obj, "description"),
                        **tr(obj, "warning"),
                    )
                    node_items = obj["nodes"].items()
                    # Premier passage : tous les nœuds sont créés sans références vers les cibles.
                    refs = {}
                    for idx, (key, node) in enumerate(node_items):
                        typ = node.get("kind", "").upper()
                        if typ not in TypeNoeud.values:
                            raise ValueError(f"{slug}:{key}: kind inconnu")
                        visual = Visuel.objects.filter(
                            code=node.get("visual", "")
                        ).first()
                        if node.get("visual") and not visual:
                            raise ValueError(
                                f'{slug}:{key}: visuel inconnu {node.get("visual")}'
                            )
                        # Les scènes sont provisoirement enregistrées comme ENDING pour respecter le CHECK SQL
                        # jusqu'à la résolution atomique de leur ForeignKey next.
                        refs[key] = Noeud.objects.create(
                            tantara=s,
                            cle=key,
                            type="ENDING" if typ == "SCENE" else typ,
                            tag=node.get("tag", ""),
                            visuel=visual,
                            poids=node.get("weight") if typ == "DECISION" else None,
                            ordre=idx,
                            **tr(node, "title"),
                            **tr(node, "text"),
                        )
                    # Deuxième passage : résolution des relations.
                    for key, node in obj["nodes"].items():
                        source = refs[key]
                        if node.get("kind", "").upper() == "SCENE":
                            target = node.get("next")
                            if target not in refs:
                                raise ValueError(f"{slug}:{key}: next inconnu {target}")
                            source.type = "SCENE"
                            source.noeud_suivant = refs[target]
                            source.save(
                                update_fields=["type", "noeud_suivant", "updated_at"]
                            )
                        if source.type == "DECISION":
                            for i, option in enumerate(node.get("options", [])):
                                target = option.get("next")
                                if target not in refs:
                                    raise ValueError(
                                        f"{slug}:{key}: option.next inconnu {target}"
                                    )
                                OptionDecision.objects.create(
                                    noeud=source,
                                    cle=option["id"],
                                    qualite=Decimal(str(option["quality"])),
                                    noeud_cible=refs[target],
                                    ordre=i,
                                    **tr(option, "label"),
                                    **tr(option, "feedback"),
                                )
                self.stdout.write(
                    self.style.SUCCESS(
                        "Brouillons importés. Aucune approbation automatique."
                    )
                )
        except (ValueError, KeyError, TypeError) as e:
            raise CommandError(str(e)) from e

    def _catalog(self, root):
        p = root / "visuals.json"
        if p.exists():
            for x in read_json(p):
                Visuel.objects.update_or_create(
                    code=x["code"],
                    defaults={
                        "type": x["type"].upper(),
                        "chemin_asset": x["chemin_asset"],
                        "format": x["format"].upper(),
                        "largeur_px": x.get("largeur_px"),
                        "hauteur_px": x.get("hauteur_px"),
                        "alt_fr": x.get("alt_fr", ""),
                        "alt_mg": x.get("alt_mg", ""),
                        "decoratif": x.get("decoratif", False),
                        "licence": x["licence"],
                        "url_provenance": x.get("url_provenance", ""),
                        "attribution": x.get("attribution", ""),
                        "sha256": x.get("sha256", ""),
                        "actif": x.get("actif", True),
                    },
                )
        p = root / "subjects.json"
        if p.exists():
            for x in read_json(p):
                Sujet.objects.update_or_create(
                    code=x["code"],
                    defaults={
                        **tr(x, "libelle"),
                        "description_fr": x.get("description", {}).get("fr", ""),
                        "description_mg": x.get("description", {}).get("mg", ""),
                        "ordre": x.get("ordre", 0),
                        "actif": x.get("actif", True),
                    },
                )
        p = root / "sources.json"
        if p.exists():
            for x in read_json(p):
                Source.objects.update_or_create(
                    code=x["code"],
                    defaults={
                        **tr(x, "nom"),
                        "type": x["type"].upper(),
                        "url_officielle": x.get("url_officielle", ""),
                        "portee_fr": x.get("portee", {}).get("fr", ""),
                        "portee_mg": x.get("portee", {}).get("mg", ""),
                        "dernier_controle_le": x.get("dernier_controle_le"),
                        "actif": x.get("actif", True),
                    },
                )
        p = root / "resources.json"
        if p.exists():
            for x in read_json(p):
                src = Source.objects.get(code=x["source_code"])
                RessourceAide.objects.update_or_create(
                    cle=x["id"],
                    defaults={
                        **tr(x, "title"),
                        **tr(x, "description"),
                        **tr(x, "action"),
                        **tr(x, "audience"),
                        "kind": x["kind"].upper(),
                        "href": x.get("href") or "",
                        "source": src,
                        "pour_mineurs": x.get("pour_mineurs", True),
                        "statut_service": x.get("status", "review_needed").upper(),
                        "verifie_le": x.get("verifiedAt"),
                        "verificateur_role": x.get("reviewerRole") or "",
                        "statut_editorial": StatutEditorial.BROUILLON,
                        "ordre": x.get("ordre", 0),
                    },
                )
        p = root / "questions.json"
        if p.exists():
            for x in read_json(p):
                s = Sujet.objects.get(code=x["topic"])
                QuestionPedagogique.objects.update_or_create(
                    cle=x["id"],
                    defaults={
                        "sujet": s,
                        **tr(x, "question"),
                        **tr(x, "answer"),
                        "revision": x.get("version", "1.0"),
                        "ordre": x.get("ordre", 0),
                        "statut_editorial": StatutEditorial.BROUILLON,
                    },
                )
