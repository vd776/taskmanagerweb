import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))

SQLALCHEMY_DATABASE_URI = (
    'mssql+pyodbc://u9chzolmxho9m68:0ci%40dsWyXcQ3wNr%24apemnsLYP@ne-az-sql-serv1.database.windows.net/d01jcq35qv74048?'
    'driver=ODBC+Driver+17+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no'
)


# SECURITY_LOGIN_USER_TEMPLATE = 'security/login_user.html'
SECURITY_POST_LOGIN_VIEW = 'main.projects'
# SECURITY_POST_LOGOUT_VIEW = 'main.home'
# SECURITY_LOGIN_URL = '/login'

REMEMBER_COOKIE_DURATION = timedelta(days=7)
SQLALCHEMY_TRACK_MODIFICATIONS = False
SECRET_KEY = os.urandom(24)
SECURITY_PASSWORD_SALT = os.urandom(24)
