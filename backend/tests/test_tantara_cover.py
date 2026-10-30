"""Régression : couverture dans Tantara, multipart et drf-yasg.
Lancer : python -m pytest tests/test_tantara_cover.py -q
"""
from io import BytesIO
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient
from apps.content_api.models import Tantara


def png(name="cover.png", color="blue"):
    stream = BytesIO()
    Image.new("RGB", (256, 144), color).save(stream, format="PNG")
    return SimpleUploadedFile(name, stream.getvalue(), content_type="image/png")


def values(**extra):
    data = dict(
        slug="histoire-22h47", numero="93",
        titre_fr="22:47 — Le message", sous_titre_fr="Une menace",
        theme_fr="Chantage numérique", description_fr="Un récit fictif.",
        avertissement_fr="Contenu sensible fictif.",
        duree="6 min", decisions_attendues=2, palette="default",
    )
    data.update(extra)
    return data


class TantaraCoverTests(TestCase):
    def setUp(self):
        self.files = TemporaryDirectory()
        self.media = override_settings(MEDIA_ROOT=self.files.name)
        self.media.enable()
        self.user = get_user_model().objects.create_superuser(
            username="cover-test-admin", email="admin@invalid.example", password="long-secret-123"
        )
        self.client = APIClient()
        self.client.force_login(self.user)

    def tearDown(self):
        self.media.disable()
        self.files.cleanup()

    def test_create_multipart_with_and_without_cover(self):
        response = self.client.post("/api/editor/stories/create/", values(image_cover=png()), format="multipart")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertIn("/media/covers/", response.data["image_cover_url"])
        story = Tantara.objects.get(slug="histoire-22h47")
        self.assertTrue(story.image_cover.name.endswith(".png"))
        with Image.open(story.image_cover.path) as image:
            self.assertEqual(image.format, "PNG")
        self.assertEqual(self.client.get(f"/api/editor/stories/{story.pk}/").data["image_cover_url"],
                         response.data["image_cover_url"])
        response = self.client.post("/api/editor/stories/create/", values(slug="sans-image", numero="94"), format="multipart")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertIsNone(response.data["image_cover_url"])

    def test_replace_then_remove_cover(self):
        response = self.client.post("/api/editor/stories/create/", values(image_cover=png()), format="multipart")
        self.assertEqual(response.status_code, 201, response.data)
        pk = response.data["id"]
        response = self.client.patch(f"/api/editor/stories/{pk}/partial-update/",
                                     {"image_cover":png("new.png", "red")}, format="multipart")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["image_cover_url"])
        response = self.client.patch(f"/api/editor/stories/{pk}/partial-update/",
                                     {"effacer_couverture":"true"}, format="multipart")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIsNone(response.data["image_cover_url"])
        self.assertFalse(Tantara.objects.get(pk=pk).image_cover)

    def test_reject_invalid_upload_and_conflicting_options(self):
        bad = SimpleUploadedFile("cover.png", b"not an image", content_type="image/png")
        response = self.client.post("/api/editor/stories/create/", values(image_cover=bad), format="multipart")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(Tantara.objects.count(), 0)
        response = self.client.post("/api/editor/stories/create/",
                                    values(image_cover=png(), effacer_couverture="true"), format="multipart")
        self.assertEqual(response.status_code, 400, response.data)

    def test_swagger_uses_formdata_without_request_body(self):
        from apps.content_api.swagger import tantara_docs
        # Les décorateurs sont générés avec la même source de paramètres pour les trois opérations.
        from apps.content_api.swagger import tantara_form_parameters
        fields = tantara_form_parameters(required_fields=False)
        self.assertEqual(next(f for f in fields if f.name == "image_cover").get("type"), "file")
        self.assertTrue(all(f.get("in") == "formData" and not f.get("required", False) for f in fields))
        self.assertFalse(next(f for f in fields if f.name == "titre_fr").required)
        self.assertTrue(next(f for f in tantara_form_parameters() if f.name == "titre_fr").required)
        self.assertIn("create", tantara_docs)
