"""Worker séparé. Commande : celery -A helpers.celery_app:app worker -l info -c 1"""
import os
from celery import Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
app = Celery('safidiko')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks(['apps.media_studio'])
