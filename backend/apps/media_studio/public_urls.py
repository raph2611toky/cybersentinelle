from django.urls import path
from .public_views import PublishedSceneMediaAPIView, PublishedSceneSubtitleAPIView

urlpatterns = [
    path('subtitles/<str:version>/<uuid:asset_id>/<str:ext>/', PublishedSceneSubtitleAPIView.as_view(), name='story-subtitle'),
    path('media-clips/<str:version>/<uuid:asset_id>/', PublishedSceneMediaAPIView.as_view(), name='story-media'),
]
