"""Validation de graphes avant publication. Aucun état de joueur n'est enregistré."""

from django.core.exceptions import ValidationError
from apps.core.choices import TypeNoeud


def validate_story_graph(story):
    nodes = list(
        story.noeuds.select_related("noeud_suivant", "visuel").prefetch_related(
            "options__noeud_cible"
        )
    )
    mapping = {n.cle: n for n in nodes}
    if len(mapping) != len(nodes) or "start" not in mapping:
        raise ValidationError(f"{story.slug}: nœud start absent ou clés dupliquées")
    if len(nodes) < 3:
        raise ValidationError(f"{story.slug}: histoire incomplète")
    visited_global = set()
    endings = set()

    def traverse(key, stack, decisions):
        if key not in mapping:
            raise ValidationError(f"{story.slug}: cible inconnue {key}")
        if key in stack:
            raise ValidationError(f"{story.slug}: boucle détectée sur {key}")
        n = mapping[key]
        visited_global.add(key)
        if n.type == TypeNoeud.ENDING:
            if decisions != story.decisions_attendues:
                raise ValidationError(
                    f"{story.slug}: parcours avec {decisions} décisions, attendu {story.decisions_attendues}"
                )
            endings.add(key)
            return
        if n.type == TypeNoeud.SCENE:
            if not n.noeud_suivant_id or n.noeud_suivant.tantara_id != story.pk:
                raise ValidationError(f"{story.slug}:{key}: scene.next invalide")
            traverse(n.noeud_suivant.cle, stack | {key}, decisions)
            return
        if n.type != TypeNoeud.DECISION or not n.poids or n.noeud_suivant_id:
            raise ValidationError(
                f"{story.slug}:{key}: type/poids de décision invalide"
            )
        options = list(n.options.all())
        if not 2 <= len(options) <= 3:
            raise ValidationError(f"{story.slug}:{key}: 2 ou 3 options obligatoires")
        for opt in options:
            if opt.noeud_cible.tantara_id != story.pk:
                raise ValidationError(f"{story.slug}:{key}: option inter-Tantara")
            traverse(opt.noeud_cible.cle, stack | {key}, decisions + 1)

    traverse("start", set(), 0)
    if visited_global != set(mapping):
        raise ValidationError(
            f"{story.slug}: nœuds inaccessibles {sorted(set(mapping)-visited_global)}"
        )
    if not endings:
        raise ValidationError(f"{story.slug}: aucune fin accessible")
    return True
