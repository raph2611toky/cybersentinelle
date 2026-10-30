from django.core.management.base import BaseCommand, CommandError
from apps.publication.services import rollback


class Command(BaseCommand):
    help = "Réactive une ancienne release JSON immuable après vérification."

    def add_arguments(self, parser):
        parser.add_argument("--version", required=True)

    def handle(self, *args, **opts):
        try:
            v = rollback(opts["version"])
        except Exception as e:
            raise CommandError("Rollback impossible : " + str(e)) from e
        self.stdout.write(self.style.SUCCESS(f"Active: {v.numero}"))
