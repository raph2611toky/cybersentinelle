# PyMySQL assure le client MySQL sans compilation de mysqlclient.
try:
    import pymysql

    pymysql.install_as_MySQLdb()
except ImportError:
    pass
