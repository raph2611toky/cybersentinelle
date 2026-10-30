from rest_framework.routers import DefaultRouter
from apps.core.views import LangueViewSet
from apps.content_api.views import (
    SujetViewSet,
    VisuelViewSet,
    TantaraViewSet,
    NoeudViewSet,
    OptionDecisionViewSet,
)
from apps.resources.views import SourceViewSet, RessourceAideViewSet
from apps.pedagogie.views import QuestionPedagogiqueViewSet
from apps.publication.views import ReleaseViewSet

router = DefaultRouter()
router.register("languages", LangueViewSet, basename="editor-language")
router.register("topics", SujetViewSet, basename="editor-topics")
router.register("visuals", VisuelViewSet, basename="editor-visuals")
router.register("stories", TantaraViewSet, basename="editor-stories")
router.register("nodes", NoeudViewSet, basename="editor-nodes")
router.register("options", OptionDecisionViewSet, basename="editor-options")
router.register("sources", SourceViewSet, basename="editor-sources")
router.register("resources", RessourceAideViewSet, basename="editor-resources")
router.register("questions", QuestionPedagogiqueViewSet, basename="editor-questions")
router.register("releases", ReleaseViewSet, basename="editor-release")
urlpatterns = router.urls
