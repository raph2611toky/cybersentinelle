from django.db import models
from apps.core.models import ContenuEditorial
from apps.core.validators import bilingual
from apps.content_api.models import Sujet
from apps.resources.models import RessourceAide


class QuestionPedagogique(ContenuEditorial):
    cle = models.SlugField(max_length=120, unique=True)
    sujet = models.ForeignKey(Sujet, on_delete=models.PROTECT, related_name="questions")
    question_fr = models.TextField()
    question_mg = models.TextField()
    reponse_fr = models.TextField()
    reponse_mg = models.TextField()
    ressources_liees = models.ManyToManyField(
        RessourceAide, blank=True, related_name="questions_associees"
    )
    ordre = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "pedagogie_questionpedagogique"
        ordering = ["ordre", "cle"]

    def clean(self):
        super().clean()
        bilingual(self.question_fr, self.question_mg, "Question")
        bilingual(self.reponse_fr, self.reponse_mg, "Réponse")

    def __str__(self):
        return self.cle
