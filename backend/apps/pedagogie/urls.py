from django.urls import path
from .views import QuestionsListView

urlpatterns = [path("questions/", QuestionsListView.as_view(), name="questions-list")]
