from django.urls import path
from .views import ResourcesListView

urlpatterns = [path("resources/", ResourcesListView.as_view(), name="resources-list")]
