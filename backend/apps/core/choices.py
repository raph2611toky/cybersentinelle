from django.db import models


class StatutEditorial(models.TextChoices):
    BROUILLON = "BROUILLON", "Brouillon"
    EN_RELECTURE = "EN_RELECTURE", "En relecture"
    APPROUVE = "APPROUVE", "Approuvé"
    A_CORRIGER = "A_CORRIGER", "À corriger"
    PUBLIE = "PUBLIE", "Publié"
    ARCHIVE = "ARCHIVE", "Archivé"


class TypeNoeud(models.TextChoices):
    SCENE = "SCENE", "Scène"
    DECISION = "DECISION", "Décision"
    ENDING = "ENDING", "Fin"


class TypeVisuel(models.TextChoices):
    HERO = "HERO", "Héros"
    SCENE = "SCENE", "Scène"
    ICON = "ICON", "Icône"


class TypeSource(models.TextChoices):
    SERVICE_PUBLIC = "SERVICE_PUBLIC", "Service public"
    INSTITUTION = "INSTITUTION", "Institution"
    ONG = "ONG", "ONG"
    AUTRE_ORGANISATION = "AUTRE_ORGANISATION", "Autre organisation"
    REFERENTIEL_INTERNE = "REFERENTIEL_INTERNE", "Référentiel interne"


class TypeRessource(models.TextChoices):
    CALL = "CALL", "Appel"
    EXTERNAL = "EXTERNAL", "Externe"
    INTERNAL = "INTERNAL", "Interne"


class StatutService(models.TextChoices):
    ACTIVE = "ACTIVE", "Actif"
    UNAVAILABLE = "UNAVAILABLE", "Indisponible"
    REVIEW_NEEDED = "REVIEW_NEEDED", "À vérifier"


class StatutPublication(models.TextChoices):
    PREPARATION = "PREPARATION", "Préparation"
    VALIDEE = "VALIDEE", "Validée"
    ACTIVE = "ACTIVE", "Active"
    ARCHIVEE = "ARCHIVEE", "Archivée"


class TypeFichierContenu(models.TextChoices):
    STORY = "STORY", "Histoire"
    QUESTIONS = "QUESTIONS", "Questions"
    RESOURCES = "RESOURCES", "Ressources"
