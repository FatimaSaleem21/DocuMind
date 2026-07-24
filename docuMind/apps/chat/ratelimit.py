import logging

import redis
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

SECONDS_PER_DAY = 86400


def client_ip(request):
    """Return the real client IP.

    Railway/Render terminate TLS at an edge proxy, so REMOTE_ADDR is the proxy;
    the caller's address is the first entry in X-Forwarded-For.
    """
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def over_daily_limit(request):
    """Increment a per-IP daily counter in Redis and report whether it exceeds
    CHAT_DAILY_IP_LIMIT.

    This protects the OpenAI bill on a public demo, not against determined
    abuse. It fails open: a non-positive limit disables it, and if Redis is
    unreachable the request is allowed rather than blocking the whole feature.
    """
    limit = settings.CHAT_DAILY_IP_LIMIT
    if limit <= 0:
        return False

    today = timezone.now().strftime("%Y-%m-%d")
    key = f"chat:ratelimit:{client_ip(request)}:{today}"
    try:
        conn = redis.Redis.from_url(settings.CELERY_BROKER_URL)
        count = conn.incr(key)
        if count == 1:
            # First hit today — expire the counter so it resets tomorrow.
            conn.expire(key, SECONDS_PER_DAY)
        return count > limit
    except redis.RedisError as exc:
        logger.warning("Chat rate-limit check skipped; Redis error: %s", exc)
        return False