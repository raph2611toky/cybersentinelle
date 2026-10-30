import hashlib
from django import forms
from helpers.helper import normalize_image
from .models import Visuel


class VisuelAdminForm(forms.ModelForm):
    class Meta:
        model = Visuel
        fields = "__all__"

    def clean(self):
        data = super().clean()
        if "fichier" in self.files and data.get("fichier"):
            upload = normalize_image(data["fichier"])
            data["fichier"] = upload
            data["format"] = "PNG"
            data["largeur_px"], data["hauteur_px"] = upload.image_dimensions
            data["sha256"] = hashlib.sha256(upload.read()).hexdigest()
            upload.seek(0)
        return data
