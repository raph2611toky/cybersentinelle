from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from apps.core.models import ModeleBase, ContenuEditorial
from apps.core.choices import TypeSource, TypeRessource, StatutService, StatutEditorial
from apps.core.validators import bilingual, https_or_tel


class Source(ModeleBase):
    code = models.SlugField(max_length=80, unique=True)
    nom_fr = models.CharField(max_length=200)
    nom_mg = models.CharField(max_length=200)
    type = models.CharField(max_length=24, choices=TypeSource.choices)
    url_officielle = models.URLField(blank=True)
    portee_fr = models.TextField(blank=True)
    portee_mg = models.TextField(blank=True)
    dernier_controle_le = models.DateField(null=True, blank=True)
    actif = models.BooleanField(default=True)

    class Meta:
        db_table = "resources_source"
        ordering = ["code"]

    def clean(self):
        super().clean()
        bilingual(self.nom_fr, self.nom_mg, "Source")
        if self.type != TypeSource.REFERENTIEL_INTERNE:
            if not self.url_officielle.startswith("https://"):
                raise ValidationError("Source externe exige une URL officielle HTTPS")
        elif self.url_officielle:
            raise ValidationError(
                "Source interne ne doit pas usurper une URL officielle"
            )
        if bool(self.portee_fr.strip()) != bool(self.portee_mg.strip()):
            raise ValidationError("Portée FR/MG doit être remplie ensemble")

    def __str__(self):
        return self.code


class RessourceAide(ContenuEditorial):
    cle = models.SlugField(max_length=80, unique=True)
    titre_fr = models.CharField(max_length=200)
    titre_mg = models.CharField(max_length=200)
    description_fr = models.TextField()
    description_mg = models.TextField()
    action_fr = models.CharField(max_length=255)
    action_mg = models.CharField(max_length=255)
    audience_fr = models.TextField()
    audience_mg = models.TextField()
    limites_fr = models.TextField(blank=True)
    limites_mg = models.TextField(blank=True)
    zone_fr = models.CharField(max_length=150, blank=True)
    zone_mg = models.CharField(max_length=150, blank=True)
    pour_mineurs = models.BooleanField(default=True)
    kind = models.CharField(max_length=12, choices=TypeRessource.choices)
    href = models.CharField(max_length=500, blank=True)
    source = models.ForeignKey(
        Source, on_delete=models.PROTECT, related_name="ressources"
    )
    verifie_le = models.DateField(null=True, blank=True)
    verificateur_role = models.CharField(max_length=80, blank=True)
    statut_service = models.CharField(
        max_length=20,
        choices=StatutService.choices,
        default=StatutService.REVIEW_NEEDED,
    )
    ressource_repli = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="replis_entrants",
    )
    ordre = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "resources_ressourceaide"
        ordering = ["ordre", "cle"]

    def clean(self):
        super().clean()
        for k in ("titre", "description", "action", "audience"):
            bilingual(getattr(self, k + "_fr"), getattr(self, k + "_mg"), k)
        for k in ("limites", "zone"):
            if bool(getattr(self, k + "_fr").strip()) != bool(
                getattr(self, k + "_mg").strip()
            ):
                raise ValidationError(f"{k} FR/MG doivent être renseignés ensemble")
        if self.kind == TypeRessource.INTERNAL:
            if self.href:
                raise ValidationError("Une ressource interne ne doit pas avoir de href")
            if self.source_id and self.source.type != TypeSource.REFERENTIEL_INTERNE:
                raise ValidationError("Une ressource interne exige une source interne")
        else:
            if self.href:
                https_or_tel(self.href)
            elif self.statut_service == StatutService.ACTIVE:
                raise ValidationError("Un service actif exige un contact vérifié")
            if (
                self.href
                and self.kind == TypeRessource.CALL
                and not self.href.startswith("tel:")
            ):
                raise ValidationError("CALL exige tel:")
            if (
                self.href
                and self.kind == TypeRessource.EXTERNAL
                and not self.href.startswith("https://")
            ):
                raise ValidationError("EXTERNAL exige HTTPS")
            if self.source_id and self.source.type == TypeSource.REFERENTIEL_INTERNE:
                raise ValidationError(
                    "Service externe exige une véritable source externe"
                )
        if self.verifie_le and self.verifie_le > timezone.localdate():
            raise ValidationError("Date de vérification future interdite")
        if (
            self.statut_service == StatutService.ACTIVE
            and self.kind != TypeRessource.INTERNAL
        ):
            if (
                not self.verifie_le
                or not self.verificateur_role.strip()
                or not self.source_id
                or not self.source.dernier_controle_le
            ):
                raise ValidationError(
                    "Une ressource externe ACTIVE doit être vérifiée et sourcée"
                )
        if self.ressource_repli_id and self.ressource_repli_id == self.pk:
            raise ValidationError("Une ressource ne peut pas être son propre repli")

    def __str__(self):
        return self.cle
