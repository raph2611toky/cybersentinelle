from django.db import models
from django.db.models import Q
from django.core.exceptions import ValidationError
from apps.core.models import ModeleBase, Langue
from apps.core.choices import StatutPublication, TypeFichierContenu
from apps.core.validators import sha256_validator, relative_asset


class VersionContenu(ModeleBase):
    numero = models.CharField(max_length=40, unique=True)
    statut = models.CharField(
        max_length=16,
        choices=StatutPublication.choices,
        default=StatutPublication.PREPARATION,
    )
    active_slot = models.PositiveSmallIntegerField(
        null=True, blank=True, unique=True, editable=False
    )
    date_publication = models.DateTimeField(null=True, blank=True)
    digest_global = models.CharField(
        max_length=64, blank=True, validators=[sha256_validator]
    )
    langues = models.ManyToManyField(Langue, related_name="versions_contenu")
    journal = models.TextField(blank=True)
    git_commit = models.CharField(max_length=40, blank=True)
    repertoire_snapshot = models.CharField(
        max_length=255, blank=True, validators=[relative_asset]
    )

    class Meta:
        db_table = "publication_versioncontenu"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(statut=StatutPublication.ACTIVE, active_slot=1)
                    | (
                        ~Q(statut=StatutPublication.ACTIVE)
                        & Q(active_slot__isnull=True)
                    )
                ),
                name="release_active_slot_match",
            )
        ]

    def clean(self):
        super().clean()
        if not self.numero.strip():
            raise ValidationError("Numéro obligatoire")
        if self.digest_global:
            sha256_validator(self.digest_global)
        if self.repertoire_snapshot:
            relative_asset(self.repertoire_snapshot)
        if self.statut in {
            StatutPublication.VALIDEE,
            StatutPublication.ACTIVE,
            StatutPublication.ARCHIVEE,
        }:
            if (
                not self.digest_global
                or not self.repertoire_snapshot
                or not self.date_publication
            ):
                raise ValidationError(
                    "Un manifeste finalisé requiert hash, chemin et date"
                )

    def save(self, *args, **kwargs):
        self.active_slot = 1 if self.statut == StatutPublication.ACTIVE else None
        if kwargs.get("update_fields") is not None:
            kwargs["update_fields"] = set(kwargs["update_fields"]) | {"active_slot"}
        super().save(*args, **kwargs)

    def __str__(self):
        return self.numero


class FichierContenu(ModeleBase):
    version = models.ForeignKey(
        VersionContenu, on_delete=models.CASCADE, related_name="fichiers"
    )
    chemin = models.CharField(max_length=500, validators=[relative_asset])
    type = models.CharField(max_length=16, choices=TypeFichierContenu.choices)
    sha256 = models.CharField(max_length=64, validators=[sha256_validator])
    taille_octets = models.PositiveBigIntegerField()
    langue = models.ForeignKey(
        Langue,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="fichiers_contenu",
    )
    ordre = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "publication_fichiercontenu"
        ordering = ["ordre", "chemin"]
        constraints = [
            models.UniqueConstraint(
                fields=["version", "chemin"], name="file_unique_version_path"
            )
        ]

    def clean(self):
        super().clean()
        relative_asset(self.chemin)
        sha256_validator(self.sha256)

    def __str__(self):
        return f"{self.version.numero}/{self.chemin}"
