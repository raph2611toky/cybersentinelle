from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ValidationError
from apps.publication.services import publication_payload


class Command(BaseCommand):
    help = "Valide tous les contenus sans créer de release ni modifier la base."

    def handle(self, *args, **kwargs):
        try:
            result, assets = publication_payload()
        except (ValidationError, ValueError) as e:
            raise CommandError(str(e)) from e
        self.stdout.write(
            self.style.SUCCESS(f"{len(result)} JSON et {len(assets)} assets validés.")
        )
