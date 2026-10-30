"""Marquage explicite des relectures réellement réalisées; aucun auto-approval."""

from datetime import date
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.core.choices import StatutEditorial
from apps.content_api.models import Tantara
from apps.resources.models import RessourceAide
from apps.pedagogie.models import QuestionPedagogique


class Command(BaseCommand):
    help = "Confirme une validation éditoriale et bilingue réellement effectuée (pas automatique)."

    def add_arguments(self, p):
        p.add_argument(
            "--type", required=True, choices=["story", "resource", "question"]
        )
        p.add_argument("--key", required=True)
        p.add_argument("--validateur-role", required=True)
        p.add_argument("--relecteur-fr-role", required=True)
        p.add_argument("--relecteur-mg-role", required=True)
        p.add_argument(
            "--date", required=True, help="AAAA-MM-JJ, date réelle de validation"
        )
        p.add_argument(
            "--confirm-reviewed",
            action="store_true",
            help="Atteste que la relecture humaine a été effectuée",
        )

    def handle(self, *args, **o):
        if not o["confirm_reviewed"]:
            raise CommandError(
                "--confirm-reviewed requis : validation humaine seulement"
            )
        try:
            when = date.fromisoformat(o["date"])
        except ValueError as e:
            raise CommandError("Date AAAA-MM-JJ invalide") from e
        if when > timezone.localdate():
            raise CommandError("Date de relecture future interdite")
        model = {
            "story": Tantara,
            "resource": RessourceAide,
            "question": QuestionPedagogique,
        }[o["type"]]
        field = "slug" if o["type"] == "story" else "cle"
        try:
            item = model.objects.get(**{field: o["key"]})
        except model.DoesNotExist as e:
            raise CommandError("Objet inconnu") from e
        if item.statut_editorial not in {
            StatutEditorial.BROUILLON,
            StatutEditorial.EN_RELECTURE,
            StatutEditorial.A_CORRIGER,
        }:
            raise CommandError(
                "Objet déjà approuvé/publié; ne pas modifier silencieusement"
            )
        old = {
            f: getattr(item, f)
            for f in (
                "statut_editorial",
                "valide_le",
                "validateur_role",
                "relecture_fr_le",
                "relecture_mg_le",
                "relecteur_fr_role",
                "relecteur_mg_role",
            )
        }
        item.statut_editorial = StatutEditorial.APPROUVE
        item.valide_le = when
        item.validateur_role = o["validateur_role"]
        item.relecture_fr_le = when
        item.relecture_mg_le = when
        item.relecteur_fr_role = o["relecteur_fr_role"]
        item.relecteur_mg_role = o["relecteur_mg_role"]
        try:
            item.full_clean()
        except ValidationError as e:
            for f, v in old.items():
                setattr(item, f, v)
            raise CommandError(str(e)) from e
        item.save()
        self.stdout.write(
            self.style.SUCCESS(
                f'Approuvé après relecture humaine : {o["type"]}:{o["key"]}'
            )
        )
