from django.urls import path
from .views import StoriesListView, StoryDetailView, PublishedStoryCoverAPIView

urlpatterns = [
    path("covers/<str:version>/<slug:slug>/", PublishedStoryCoverAPIView.as_view(), name="story-cover"),
    path("stories/", StoriesListView.as_view(), name="stories-list"),
    path("stories/<slug:slug>/", StoryDetailView.as_view(), name="stories-detail"),
]
