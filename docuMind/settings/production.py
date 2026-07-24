import os

import dj_database_url

from .base import *  # noqa: F401,F403

DEBUG = False

# Hard-required in production — fail loudly at boot if missing, not silently at runtime.
SECRET_KEY = os.environ['SECRET_KEY']
ALLOWED_HOSTS = os.environ['ALLOWED_HOSTS'].split(',')
CORS_ALLOWED_ORIGINS = os.environ['CORS_ALLOWED_ORIGINS'].split(',')

# Managed providers (Neon, Railway, Render) expose a single DATABASE_URL
# connection string rather than discrete POSTGRES_* vars. SSL is required and
# connections are reused across requests.
DATABASES = {
    'default': dj_database_url.parse(
        os.environ['DATABASE_URL'],
        conn_max_age=600,
        ssl_require=True,
    ),
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    *MIDDLEWARE[1:],  # noqa: F405  (MIDDLEWARE comes from the star import above)
]

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Railway/Render terminate TLS at the edge and forward this header.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# With TLS terminated at the edge, redirect any plain-HTTP traffic and lock
# cookies/HSTS to HTTPS so nothing sensitive rides over an unencrypted hop.
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True