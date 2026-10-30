from django.urls import path
from .views import TranslationStatusAPIView,TranslationRetryAPIView
urlpatterns=[
    path('status/',TranslationStatusAPIView.as_view(),name='editor-translation-status'),
    path('retry/',TranslationRetryAPIView.as_view(),name='editor-translation-retry'),
]
