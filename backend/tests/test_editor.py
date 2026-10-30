import io
import pytest
from PIL import Image
from django.contrib.auth.models import Permission, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from rest_framework.test import APIClient
from apps.content_api.models import Sujet, Tantara, Noeud, OptionDecision
from apps.core.models import Langue

pytestmark = pytest.mark.django_db


def topic_payload():
    return {"code": "respect", "libelle_fr": "Respect", "libelle_mg": "Fanajana"}


@pytest.fixture
def staff():
    return User.objects.create_superuser("editor", password="Unique-example-726!")


@pytest.fixture
def editor(staff):
    client = APIClient()
    client.force_login(staff)
    return client


@pytest.mark.parametrize(
    "route",
    [
        "languages",
        "topics",
        "visuals",
        "stories",
        "nodes",
        "options",
        "sources",
        "resources",
        "questions",
        "releases",
    ],
)
def test_anonymous_cannot_access_editor(route):
    c = APIClient()
    url = "/api/editor/" + route + "/"
    assert c.get(url).status_code == 403
    assert c.post(url + "create/", {}, format="json").status_code == 403


def test_nonstaff_and_staff_without_permissions_denied():
    user = User.objects.create_user("ordinary", password="pw")
    c = APIClient()
    c.force_login(user)
    assert c.get("/api/editor/topics/").status_code == 403
    user.is_staff = True
    user.save()
    assert c.get("/api/editor/topics/").status_code == 403
    user.user_permissions.add(Permission.objects.get(codename="view_sujet"))
    assert c.get("/api/editor/topics/").status_code == 200
    assert c.post("/api/editor/topics/create/", topic_payload()).status_code == 403


def test_topic_complete_crud(editor):
    r = editor.post("/api/editor/topics/create/", topic_payload(), format="json")
    assert r.status_code == 201, r.data
    url = "/api/editor/topics/" + r.data["id"] + "/"
    assert editor.get(url).data["libelle_fr"] == "Respect"
    assert editor.get("/api/editor/topics/").data["count"] == 1
    assert (
        editor.patch(url + "partial-update/", {"libelle_fr": "Respect mutuel"}, format="json").status_code
        == 200
    )
    assert editor.put(url + "update/", topic_payload(), format="json").status_code == 200
    assert editor.delete(url + "delete/").status_code == 200
    assert editor.get(url).status_code == 404


def test_validation_returns_field_errors(editor):
    r = editor.post(
        "/api/editor/topics/create/",
        {"code": "x", "libelle_fr": "X", "libelle_mg": ""},
        format="json",
    )
    assert r.status_code == 400
    assert "fields" in r.data["error"]
    assert not Sujet.objects.exists()


def test_partial_update_runs_model_validation(editor):
    topic = Sujet.objects.create(**topic_payload())
    r = editor.patch(
        f"/api/editor/topics/{topic.pk}/partial-update/", {"description_fr": "Seule"}, format="json"
    )
    assert r.status_code == 400
    topic.refresh_from_db()
    assert topic.description_fr == ""


def test_language_default_slot_validation(editor):
    data = dict(
        code="fr",
        nom_fr="Français",
        nom_mg="Frantsay",
        nom_natif="Français",
        par_defaut=True,
    )
    r = editor.post("/api/editor/languages/create/", data, format="json")
    assert r.status_code == 201, r.data
    assert Langue.objects.get().default_slot == 1


def make_story(slug="new-story", numero="04"):
    return Tantara.objects.create(
        slug=slug,
        numero=numero,
        titre_fr="Titre",
        titre_mg="Lohateny",
        sous_titre_fr="Sous",
        sous_titre_mg="Sous",
        theme_fr="Respect",
        theme_mg="Fanajana",
        description_fr="D",
        description_mg="D",
        avertissement_fr="A",
        avertissement_mg="A",
        duree="2 min",
        decisions_attendues=1,
        palette="green",
    )


def test_new_story_not_limited_to_three(editor):
    s = make_story()
    r = editor.patch(
        f"/api/editor/stories/{s.pk}/partial-update/", {"titre_fr": "Nouvelle histoire"}, format="json"
    )
    assert r.status_code == 200, r.data


def test_cross_story_transition_rejected(editor):
    a, b = make_story(), make_story("other", "05")
    target = Noeud.objects.create(
        tantara=b,
        cle="end",
        type="ENDING",
        titre_fr="F",
        titre_mg="F",
        texte_fr="T",
        texte_mg="T",
    )
    data = dict(
        tantara=str(a.pk),
        cle="start",
        type="SCENE",
        titre_fr="S",
        titre_mg="S",
        texte_fr="T",
        texte_mg="T",
        noeud_suivant=str(target.pk),
    )
    r = editor.post("/api/editor/nodes/create/", data, format="json")
    assert r.status_code == 400, r.data


def test_delete_protected_target_returns_conflict(editor):
    story = make_story()
    end = Noeud.objects.create(
        tantara=story,
        cle="end",
        type="ENDING",
        titre_fr="F",
        titre_mg="F",
        texte_fr="T",
        texte_mg="T",
    )
    Noeud.objects.create(
        tantara=story,
        cle="start",
        type="SCENE",
        titre_fr="S",
        titre_mg="S",
        texte_fr="T",
        texte_mg="T",
        noeud_suivant=end,
    )
    r = editor.delete(f"/api/editor/nodes/{end.pk}/delete/")
    assert r.status_code == 409
    assert Noeud.objects.count() == 2


def test_csrf_required_for_staff_writes(staff):
    c = Client(enforce_csrf_checks=True)
    c.force_login(staff)
    assert c.post("/api/editor/topics/create/", topic_payload()).status_code == 403
    c.get("/admin/")
    token = c.cookies["csrftoken"].value
    assert (
        c.post(
            "/api/editor/topics/create/",
            topic_payload(),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        ).status_code
        == 201
    )


def test_visitor_session_endpoint_absent():
    """Aucun stockage de session de joueur sur le backend public."""
    r = Client().get('/api/session/')
    assert r.status_code == 404
    assert r.json()['error']['code'] == 'NOT_FOUND'


def test_admin_registered_and_docs_protected(editor):
    assert Client().get("/api/docs/").status_code == 302
    assert editor.get("/admin/").status_code == 200
    for app, model in [
        ("core", "langue"),
        ("content_api", "tantara"),
        ("resources", "source"),
        ("pedagogie", "questionpedagogique"),
        ("publication", "versioncontenu"),
    ]:
        assert editor.get(f"/admin/{app}/{model}/").status_code == 200
    response = editor.get("/api/swagger.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert any("/editor/stories/" in key for key in paths)


def test_upload_reencoded_under_media(editor, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    raw = io.BytesIO()
    Image.new("RGB", (10, 10), "green").save(raw, "PNG")
    data = dict(
        code="hero",
        type="HERO",
        fichier=SimpleUploadedFile(
            "input.png", raw.getvalue(), content_type="image/png"
        ),
        format="PNG",
        alt_fr="Image",
        alt_mg="Sary",
        licence="CC0",
    )
    r = editor.post("/api/editor/visuals/create/", data, format="multipart")
    assert r.status_code == 201, r.data
    assert r.data["fichier"].endswith(".png")
    assert list(tmp_path.rglob("*.png"))


def test_release_is_not_arbitrary_crud(editor):
    assert editor.post("/api/editor/releases/", {}, format="json").status_code == 405
    assert (
        editor.post(
            "/api/editor/releases/publish/", {"numero": "../bad"}, format="json"
        ).status_code
        == 400
    )


def test_publication_end_to_end(editor, settings, tmp_path):
    from django.utils import timezone
    from apps.content_api.models import Visuel

    settings.MEDIA_ROOT = tmp_path / "media"
    settings.MEDIA_ROOT.mkdir()
    settings.CONTENT_ROOT = tmp_path / "content"
    settings.RELEASES_ROOT = settings.CONTENT_ROOT / "releases"
    for code in ["fr", "mg"]:
        Langue.objects.create(code=code, nom_fr=code, nom_mg=code, nom_natif=code)
    Image.new("RGB", (10, 10), "green").save(settings.MEDIA_ROOT / "hero.png")
    visual = Visuel.objects.create(
        code="hero",
        type="HERO",
        chemin_asset="hero.png",
        format="PNG",
        alt_fr="Image",
        alt_mg="Sary",
        licence="CC0",
    )
    story = make_story()
    story.visuel_heros = visual
    story.statut_editorial = "APPROUVE"
    story.valide_le = story.relecture_fr_le = story.relecture_mg_le = (
        timezone.localdate()
    )
    story.validateur_role = story.relecteur_fr_role = story.relecteur_mg_role = (
        "Relecteur"
    )
    story.save()
    start = Noeud.objects.create(
        tantara=story,
        cle="start",
        type="DECISION",
        poids=1,
        titre_fr="Choix",
        titre_mg="Safidy",
        texte_fr="T",
        texte_mg="T",
    )
    for i in range(2):
        end = Noeud.objects.create(
            tantara=story,
            cle=f"end-{i}",
            type="ENDING",
            titre_fr="Fin",
            titre_mg="Farany",
            texte_fr="T",
            texte_mg="T",
        )
        OptionDecision.objects.create(
            noeud=start,
            cle=f"choice-{i}",
            label_fr="A",
            label_mg="B",
            feedback_fr="F",
            feedback_mg="F",
            qualite=i,
            noeud_cible=end,
            ordre=i,
        )
    assert editor.get("/api/editor/releases/validate/").status_code == 200
    r = editor.post("/api/editor/releases/publish/", {"numero": "v1"}, format="json")
    assert r.status_code == 201, r.data
    first = r.data["id"]
    public = Client()
    listing = public.get("/api/v1/stories/")
    assert listing.status_code == 200
    assert not listing.cookies
    assert listing.json()[0]["id"] == "new-story"
    detail = public.get("/api/v1/stories/new-story/").json()
    assert len(detail["nodes"]) == 3
    assert "/media/hero.png" in detail["heroVisual_url"]
    assert public.get("/api/v1/stories/missing/").status_code == 404
    assert (
        editor.post(
            "/api/editor/releases/publish/", {"numero": "v2"}, format="json"
        ).status_code
        == 201
    )
    assert (
        editor.post(
            f"/api/editor/releases/{first}/rollback/", {}, format="json"
        ).status_code
        == 200
    )
    assert public.get("/api/v1/content-version/").json()["version"] == "v1"
    assert editor.delete(f"/api/editor/releases/{first}/").status_code == 405


def test_bootstrap_admin_validates_password_and_does_not_overwrite():
    from django.core.management import call_command
    from django.core.management.base import CommandError
    from unittest.mock import patch

    with patch.dict("os.environ", {"DJANGO_SUPERUSER_PASSWORD": "123"}):
        with pytest.raises(CommandError):
            call_command("bootstrap_admin", username="newadmin", no_input=True)
    with patch.dict(
        "os.environ", {"DJANGO_SUPERUSER_PASSWORD": "A-unique-test-passphrase-9842!"}
    ):
        call_command("bootstrap_admin", username="newadmin", no_input=True)
        with pytest.raises(CommandError):
            call_command("bootstrap_admin", username="newadmin", no_input=True)
    assert User.objects.get(username="newadmin").is_superuser


def test_relation_summary(editor):
    from apps.resources.models import Source

    source = Source.objects.create(
        code="internal", nom_fr="Interne", nom_mg="Anatiny", type="REFERENTIEL_INTERNE"
    )
    data = {
        "cle": "help",
        "source": str(source.pk),
        "kind": "INTERNAL",
        "titre_fr": "Aide",
        "titre_mg": "Fanampiana",
        "description_fr": "D",
        "description_mg": "D",
        "action_fr": "A",
        "action_mg": "A",
        "audience_fr": "Tous",
        "audience_mg": "Rehetra",
    }
    r = editor.post("/api/editor/resources/create/", data, format="json")
    assert r.status_code == 201, r.data
    assert r.data["source_detail"] == {"id": str(source.pk), "label": "internal"}
    assert editor.delete(f"/api/editor/sources/{source.pk}/delete/").status_code == 409
