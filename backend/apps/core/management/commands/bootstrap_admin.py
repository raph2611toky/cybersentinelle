import os
from getpass import getpass
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        "Crée un superutilisateur sans mot de passe par défaut ni écrasement de compte."
    )

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument("--email", default="")
        parser.add_argument("--no-input", action="store_true")

    def handle(self, *args, **options):
        User = get_user_model()
        if User.objects.filter(username=options["username"]).exists():
            raise CommandError("Ce compte existe déjà. Aucun changement effectué.")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
        if not password and options["no_input"]:
            raise CommandError(
                "DJANGO_SUPERUSER_PASSWORD requis en mode non interactif."
            )
        if not password:
            password = getpass("Mot de passe administrateur : ")
            if password != getpass("Confirmation : "):
                raise CommandError("Les mots de passe diffèrent.")
        user = User(username=options["username"], email=options["email"])
        try:
            validate_password(password, user=user)
        except ValidationError as exc:
            raise CommandError("; ".join(exc.messages)) from exc
        User.objects.create_superuser(
            username=user.username, email=user.email, password=password
        )
        self.stdout.write(self.style.SUCCESS("Administrateur créé."))
