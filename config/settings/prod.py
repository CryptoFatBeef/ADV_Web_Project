import dj_database_url
from decouple import Csv, config

from .base import *  # noqa: F401, F403

DEBUG = False

DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL'),
        conn_max_age=600,
        ssl_require=True,
    )
}

ALLOWED_HOSTS = config('DJANGO_ALLOWED_HOSTS', cast=Csv())

INSTALLED_APPS += ['storages']  # noqa: F405

# HTTPS / security headers
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = 'DENY'
