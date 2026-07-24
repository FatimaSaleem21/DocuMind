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

# User uploads (media) go to S3-compatible object storage so the web and worker
# containers share one filesystem-of-record — local disk isn't shared between
# them and is ephemeral on the host. Static files stay on WhiteNoise.
# Works with any S3-compatible provider (Cloudflare R2, AWS S3, Backblaze B2);
# for R2, AWS_S3_ENDPOINT_URL is the account endpoint and region is 'auto'.
STORAGES = {
    'default': {
        'BACKEND': 'storages.backends.s3boto3.S3Boto3Storage',
        'OPTIONS': {
            'access_key': os.environ['AWS_ACCESS_KEY_ID'],
            'secret_key': os.environ['AWS_SECRET_ACCESS_KEY'],
            'bucket_name': os.environ['AWS_STORAGE_BUCKET_NAME'],
            'endpoint_url': os.environ['AWS_S3_ENDPOINT_URL'],
            'region_name': os.environ.get('AWS_S3_REGION_NAME', 'auto'),
            'signature_version': 's3v4',
        },
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

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