from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ValidationError
from apps.publication.services import publish


class Command(BaseCommand):
    help = "Valide les contenus et publie une release JSON immuable (sans utilisateur)."

    def add_arguments(self, parser):
        parser.add_argument("--version", required=True)
        parser.add_argument("--journal", default="")

    def handle(self, *args, **opts):
        try:
            version = publish(opts["version"], opts["journal"])
        except (ValidationError, ValueError) as e:
            raise CommandError(str(e)) from e
        self.stdout.write(
            self.style.SUCCESS(
                f"Publication {version.numero} active, SHA256={version.digest_global}"
            )
        )
