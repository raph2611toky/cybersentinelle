"""Configuration de Celery, sans substitut PyMySQL : mysqlclient gère MySQLdb."""
from .celery import app as celery_app

__all__ = ("celery_app",)
