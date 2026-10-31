"""Référentiels éditoriaux minimaux pour le dashboard SAFIDIKO.

Ne crée ni données de mineurs, ni histoires, ni ressources externes ou voix API.
La commande peut être relancée à chaque déploiement sans modifier les données
existantes. Ne pas utiliser import_public_content pour ce besoin : cette commande
est un import de récits et refuse les histoires déjà présentes.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.content_api.models import Sujet
from apps.core.models import Langue
from apps.core.choices import TypeSource
from apps.resources.models import Source


LANGUES = (
    ("fr", {"nom_fr": "Français", "nom_mg": "Frantsay", "nom_natif": "Français", "par_defaut": False, "actif": True, "ordre": 0}),
    ("mg", {"nom_fr": "Malgache", "nom_mg": "Malagasy", "nom_natif": "Malagasy", "par_defaut": False, "actif": True, "ordre": 1}),
)

SUJETS = (
    ("cyberharcelement", "Cyberharcèlement", "Fanorisorenana an-tserasera"),
    ("rumeurs", "Rumeurs et humiliations", "Tsaho sy fanalam-baraka"),
    ("videos-manipulees", "Vidéos manipulées", "Lahatsary novaina"),
    ("partage-sans-consentement", "Diffusion sans consentement", "Fizarana tsy nahazoana alalana"),
    ("chantage-numerique", "Chantage numérique", "Fandrahonana an-tserasera"),
    ("soutien-signalement", "Soutien et signalement", "Fanohanana sy fanaovana tatitra"),
)

SOURCE_INTERNE = {
    "nom_fr": "Référentiel interne Safidiko",
    "nom_mg": "Loharanom-baovao anatiny Safidiko",
    "type": TypeSource.REFERENTIEL_INTERNE,
    "url_officielle": "",  # Jamais inventer un site ou un contact officiel.
    "portee_fr": "Conseils éditoriaux fictifs de Safidiko.",
    "portee_mg": "Torohevitra noforonina ao amin\'ny Safidiko.",
    "actif": True,
}


class Command(BaseCommand):
    help = "Crée, si absents, les référentiels de base du dashboard (FR/MG, sujets, source interne)."

    def handle(self, *args, **options):
        created = {"langues": 0, "sujets": 0, "sources": 0}
        with transaction.atomic():
            # get_or_create ne remplace jamais une décision de l'administrateur.
            for code, defaults in LANGUES:
                _, added = Langue.objects.get_or_create(code=code, defaults=defaults)
                created["langues"] += int(added)

            # Ne pas remplacer le choix de langue par défaut existant.
            if not Langue.objects.filter(par_defaut=True).exists():
                langue = Langue.objects.filter(code="fr", actif=True).first()
                if langue is None:
                    langue = Langue.objects.filter(actif=True).order_by("ordre", "code").first()
                if langue is None:
                    raise CommandError(
                        "Aucune langue active : activer fr ou mg dans l'administration."
                    )
                langue.par_defaut = True
                langue.save(update_fields=["par_defaut"])

            for idx, (code, fr, mg) in enumerate(SUJETS):
                _, added = Sujet.objects.get_or_create(
                    code=code,
                    defaults={"libelle_fr": fr, "libelle_mg": mg, "actif": True, "ordre": idx},
                )
                created["sujets"] += int(added)

            _, added = Source.objects.get_or_create(
                code="referentiel-safidiko", defaults=SOURCE_INTERNE
            )
            created["sources"] += int(added)

        self.stdout.write(self.style.SUCCESS(
            "Seed SAFIDIKO OK : "
            f"{created['langues']} langue(s), "
            f"{created['sujets']} sujet(s), "
            f"{created['sources']} source(s) interne(s) créés. "
            "Enregistrements existants conservés."
        ))
