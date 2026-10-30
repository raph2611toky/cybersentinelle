from django.urls import path
from .views import StoriesListView, StoryDetailView

urlpatterns = [
    path("stories/", StoriesListView.as_view(), name="stories-list"),
    path("stories/<slug:slug>/", StoryDetailView.as_view(), name="stories-detail"),
]
