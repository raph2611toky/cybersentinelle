# PyMySQL assure le client MySQL sans compilation de mysqlclient.
try:
    import pymysql

    pymysql.install_as_MySQLdb()
except ImportError:
    pass

# Celery automatically discovers studio and translation tasks.
from .celery import app as celery_app
__all__ = ("celery_app",)
