import uuid
from django.db import models
from django.db.models import Q
from django.core.exceptions import ValidationError
from .choices import StatutEditorial
from .validators import bilingual


class ModeleBase(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ContenuEditorial(ModeleBase):
    revision = models.CharField(max_length=20, default="1.0")
    statut_editorial = models.CharField(
        max_length=20,
        choices=StatutEditorial.choices,
        default=StatutEditorial.BROUILLON,
    )
    valide_le = models.DateField(null=True, blank=True)
    validateur_role = models.CharField(max_length=80, blank=True, default="")
    relecture_fr_le = models.DateField(null=True, blank=True)
    relecture_mg_le = models.DateField(null=True, blank=True)
    relecteur_fr_role = models.CharField(max_length=80, blank=True, default="")
    relecteur_mg_role = models.CharField(max_length=80, blank=True, default="")
    note_validation = models.TextField(blank=True, default="")
    publie_le = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def clean(self):
        super().clean()
        if not self.revision.strip():
            raise ValidationError({"revision": "Révision obligatoire"})
        if self.statut_editorial in {StatutEditorial.APPROUVE, StatutEditorial.PUBLIE}:
            if not self.valide_le or not self.validateur_role.strip():
                raise ValidationError(
                    "Date et rôle de validation nécessaires avant approbation"
                )
        if self.statut_editorial == StatutEditorial.PUBLIE:
            if not all(
                [
                    self.relecture_fr_le,
                    self.relecture_mg_le,
                    self.relecteur_fr_role.strip(),
                    self.relecteur_mg_role.strip(),
                ]
            ):
                raise ValidationError(
                    "Les deux relectures linguistiques sont obligatoires"
                )


class Langue(ModeleBase):
    code = models.CharField(
        max_length=2, unique=True, choices=[("fr", "Français"), ("mg", "Malagasy")]
    )
    nom_fr = models.CharField(max_length=60)
    nom_mg = models.CharField(max_length=60)
    nom_natif = models.CharField(max_length=60)
    par_defaut = models.BooleanField(default=False)
    # Unique portable SQLite/MySQL : plusieurs NULL, une seule valeur 1.
    default_slot = models.PositiveSmallIntegerField(
        null=True, blank=True, unique=True, editable=False
    )
    actif = models.BooleanField(default=True)
    ordre = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "core_langue"
        ordering = ["ordre", "code"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(par_defaut=True, default_slot=1)
                    | Q(par_defaut=False, default_slot__isnull=True)
                ),
                name="core_default_slot_match",
            )
        ]

    def save(self, *args, **kwargs):
        self.default_slot = 1 if self.par_defaut else None
        if kwargs.get("update_fields") is not None:
            kwargs["update_fields"] = set(kwargs["update_fields"]) | {"default_slot"}
        super().save(*args, **kwargs)

    def __str__(self):
        return self.code

    def clean(self):
        super().clean()
        bilingual(self.nom_fr, self.nom_mg, "Nom de langue")
        if self.par_defaut and not self.actif:
            raise ValidationError("Langue par défaut doit être active")
