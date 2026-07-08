from django.db import connection
from django.http import JsonResponse

import redis
from django.conf import settings

from docuMind.celery import app as celery_app


def health(request):
    """Liveness/readiness check: reports app, database, and redis status."""
    checks = {}
    ok = True

    # Database
    try:
        connection.ensure_connection()
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc}"
        ok = False

    # Redis (Celery broker)
    try:
        client = redis.Redis.from_url(settings.CELERY_BROKER_URL)
        client.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"
        ok = False

    # Celery worker
    try:
        replies = celery_app.control.ping(timeout=1.0)
        if replies:
            checks["celery"] = f"ok ({len(replies)} worker(s))"
        else:
            checks["celery"] = "error: no workers responded"
            ok = False
    except Exception as exc:
        checks["celery"] = f"error: {exc}"
        ok = False

    status = 200 if ok else 503
    return JsonResponse({"status": "ok" if ok else "unhealthy", "checks": checks}, status=status)
