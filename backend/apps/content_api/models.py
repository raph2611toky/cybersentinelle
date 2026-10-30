from decimal import Decimal
from django.db import models
from django.db.models import Q
from django.core.exceptions import ValidationError
from apps.core.models import ModeleBase, ContenuEditorial
from apps.core.choices import TypeNoeud, TypeVisuel
from apps.core.validators import bilingual, relative_asset, sha256_validator


class Sujet(ModeleBase):
    code = models.SlugField(max_length=80, unique=True)
    libelle_fr = models.CharField(max_length=150)
    libelle_mg = models.CharField(max_length=150)
    description_fr = models.TextField(blank=True)
    description_mg = models.TextField(blank=True)
    ordre = models.PositiveSmallIntegerField(default=0)
    actif = models.BooleanField(default=True)

    class Meta:
        db_table = "content_api_sujet"
        ordering = ["ordre", "code"]

    def clean(self):
        super().clean()
        bilingual(self.libelle_fr, self.libelle_mg, "Sujet")
        if bool(self.description_fr.strip()) != bool(self.description_mg.strip()):
            raise ValidationError("Descriptions FR/MG doivent être fournies ensemble")

    def __str__(self):
        return self.code


class Visuel(ModeleBase):
    code = models.SlugField(max_length=80, unique=True)
    type = models.CharField(max_length=12, choices=TypeVisuel.choices)
    fichier = models.ImageField(upload_to="visuals/%Y/%m/", blank=True)
    chemin_asset = models.CharField(
        max_length=255, blank=True, validators=[relative_asset]
    )
    format = models.CharField(
        max_length=8,
        choices=[("SVG", "SVG"), ("PNG", "PNG"), ("WEBP", "WEBP"), ("JPEG", "JPEG")],
    )
    largeur_px = models.PositiveIntegerField(null=True, blank=True)
    hauteur_px = models.PositiveIntegerField(null=True, blank=True)
    alt_fr = models.CharField(max_length=255, blank=True)
    alt_mg = models.CharField(max_length=255, blank=True)
    decoratif = models.BooleanField(default=False)
    licence = models.CharField(max_length=100)
    url_provenance = models.URLField(blank=True)
    attribution = models.CharField(max_length=255, blank=True)
    sha256 = models.CharField(max_length=64, blank=True)
    actif = models.BooleanField(default=True)

    class Meta:
        db_table = "content_api_visuel"
        ordering = ["code"]

    def clean(self):
        super().clean()
        if not self.fichier and not self.chemin_asset:
            raise ValidationError(
                {"fichier": "Un fichier ou un chemin de média est requis."}
            )
        if not self.decoratif:
            bilingual(self.alt_fr, self.alt_mg, "Texte alternatif")
        if self.sha256:
            sha256_validator(self.sha256)
        if not self.licence.strip():
            raise ValidationError({"licence": "Licence/provenance obligatoire"})
        if (self.largeur_px is None) != (self.hauteur_px is None):
            raise ValidationError("Largeur et hauteur doivent être fournies ensemble")

    def __str__(self):
        return self.code


class Tantara(ContenuEditorial):
    slug = models.SlugField(max_length=40, unique=True)
    numero = models.CharField(max_length=2, unique=True)
    titre_fr = models.CharField(max_length=160)
    titre_mg = models.CharField(max_length=160)
    sous_titre_fr = models.CharField(max_length=255)
    sous_titre_mg = models.CharField(max_length=255)
    theme_fr = models.CharField(max_length=150)
    theme_mg = models.CharField(max_length=150)
    description_fr = models.TextField()
    description_mg = models.TextField()
    avertissement_fr = models.TextField()
    avertissement_mg = models.TextField()
    duree = models.CharField(max_length=40)
    decisions_attendues = models.PositiveSmallIntegerField()
    palette = models.SlugField(max_length=60)
    visuel_heros = models.ForeignKey(
        Visuel,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="histoires_hero",
    )
    sujets = models.ManyToManyField(Sujet, blank=True, related_name="tantara")
    ordre = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "content_api_tantara"
        ordering = ["ordre", "numero"]
        constraints = [
            models.CheckConstraint(
                condition=Q(decisions_attendues__gte=1),
                name="tantara_decisions_positive",
            )
        ]

    def clean(self):
        super().clean()
        for key in ("titre", "sous_titre", "theme", "description", "avertissement"):
            bilingual(getattr(self, key + "_fr"), getattr(self, key + "_mg"), key)
        if not self.duree.strip() or not self.palette.strip():
            raise ValidationError("Durée et palette obligatoires")
        if self.visuel_heros and self.visuel_heros.type != TypeVisuel.HERO:
            raise ValidationError("Le visuel héros doit être de type HERO")

    def __str__(self):
        return self.slug


class Noeud(ModeleBase):
    tantara = models.ForeignKey(
        Tantara, on_delete=models.CASCADE, related_name="noeuds"
    )
    cle = models.SlugField(max_length=80)
    type = models.CharField(max_length=12, choices=TypeNoeud.choices)
    titre_fr = models.CharField(max_length=200)
    titre_mg = models.CharField(max_length=200)
    texte_fr = models.TextField()
    texte_mg = models.TextField()
    tag = models.SlugField(max_length=60, blank=True)
    visuel = models.ForeignKey(
        Visuel, null=True, blank=True, on_delete=models.PROTECT, related_name="noeuds"
    )
    poids = models.PositiveSmallIntegerField(null=True, blank=True)
    noeud_suivant = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.RESTRICT,
        related_name="scenes_entrantes",
    )
    ordre = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "content_api_noeud"
        ordering = ["ordre", "cle"]
        constraints = [
            models.UniqueConstraint(
                fields=["tantara", "cle"], name="node_unique_story_key"
            ),
            models.CheckConstraint(
                condition=(
                    Q(type="SCENE", noeud_suivant__isnull=False, poids__isnull=True)
                    | Q(type="DECISION", noeud_suivant__isnull=True, poids__gt=0)
                    | Q(type="ENDING", noeud_suivant__isnull=True, poids__isnull=True)
                ),
                name="node_shape_by_kind",
            ),
        ]

    def clean(self):
        super().clean()
        if not self._state.adding:
            original = type(self).objects.get(pk=self.pk)
            if self.tantara_id != original.tantara_id:
                raise ValidationError({"tantara": "Le parent ne peut pas être changé."})
            if self.type != original.type and self.options.exists():
                raise ValidationError(
                    {"type": "Retirer les options avant de changer le type."}
                )
        bilingual(self.titre_fr, self.titre_mg, "Titre du nœud")
        bilingual(self.texte_fr, self.texte_mg, "Texte du nœud")
        if self.type == TypeNoeud.SCENE:
            if self.noeud_suivant_id is None or self.poids is not None:
                raise ValidationError("Une scène exige next et ne porte pas de poids")
        elif self.type == TypeNoeud.DECISION:
            if not self.poids or self.noeud_suivant_id is not None:
                raise ValidationError(
                    "Une décision exige weight > 0 et aucune transition directe"
                )
        elif self.type == TypeNoeud.ENDING:
            if self.noeud_suivant_id is not None or self.poids is not None:
                raise ValidationError("Une fin ne porte ni weight ni next")
        if self.noeud_suivant_id and self.noeud_suivant.tantara_id != self.tantara_id:
            raise ValidationError("Transition vers un autre Tantara interdite")
        if self.visuel and self.visuel.type not in (TypeVisuel.SCENE, TypeVisuel.ICON):
            raise ValidationError("Type de visuel invalide pour un nœud")

    def __str__(self):
        return f"{self.tantara.slug}:{self.cle}"


class OptionDecision(ModeleBase):
    noeud = models.ForeignKey(Noeud, on_delete=models.CASCADE, related_name="options")
    cle = models.SlugField(max_length=80)
    label_fr = models.CharField(max_length=255)
    label_mg = models.CharField(max_length=255)
    feedback_fr = models.TextField()
    feedback_mg = models.TextField()
    qualite = models.DecimalField(max_digits=4, decimal_places=3)
    noeud_cible = models.ForeignKey(
        Noeud, on_delete=models.RESTRICT, related_name="options_entrantes"
    )
    ordre = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "content_api_optiondecision"
        ordering = ["ordre", "cle"]
        constraints = [
            models.UniqueConstraint(
                fields=["noeud", "cle"], name="option_unique_node_key"
            ),
            models.UniqueConstraint(
                fields=["noeud", "ordre"], name="option_unique_node_order"
            ),
            models.CheckConstraint(
                condition=Q(qualite__gte=Decimal("0")) & Q(qualite__lte=Decimal("1")),
                name="option_quality_0_1",
            ),
        ]

    def clean(self):
        super().clean()
        if (
            not self._state.adding
            and type(self).objects.get(pk=self.pk).noeud_id != self.noeud_id
        ):
            raise ValidationError({"noeud": "Le parent ne peut pas être changé."})
        bilingual(self.label_fr, self.label_mg, "Label")
        bilingual(self.feedback_fr, self.feedback_mg, "Feedback")
        if self.qualite is None or not (Decimal("0") <= self.qualite <= Decimal("1")):
            raise ValidationError("Qualité doit être entre 0 et 1")
        if self.noeud_id and self.noeud.type != TypeNoeud.DECISION:
            raise ValidationError("Une option ne peut être liée qu’à une décision")
        if (
            self.noeud_id
            and self.noeud_cible_id
            and self.noeud.tantara_id != self.noeud_cible.tantara_id
        ):
            raise ValidationError("Transition inter-Tantara interdite")

    def __str__(self):
        return f"{self.noeud}:{self.cle}"


class BrouillonGraphe(models.Model):
    """État graphique privé du studio ; distinct des nœuds validés/publiables."""
    tantara = models.OneToOneField(Tantara, on_delete=models.CASCADE, related_name='brouillon_graphe')
    graphe = models.JSONField(default=dict)
    revision = models.PositiveIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'content_api_brouillon_graphe'
