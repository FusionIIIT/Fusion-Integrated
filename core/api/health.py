from django.conf import settings
from django.db import connection
from django.http import JsonResponse


def healthz(_request):
    """Liveness. Checks nothing external on purpose — a probe that fails when
    Postgres blips would restart a healthy process during an incident."""
    return JsonResponse({"status": "ok"})


def _broker(checks: dict) -> bool:
    """An LRU broker drops queued tasks with no error anywhere, so the policy is
    worth a probe: silence is exactly what the failure looks like."""
    url = getattr(settings, "CELERY_BROKER_URL", "") or ""
    if not url.startswith("redis"):
        # memory:// is normal in dev and tests; prod refuses to boot without a
        # real broker, so there is nothing to fail here.
        checks["broker"] = f"not redis ({url or 'unset'})"
        return True
    try:
        import redis

        policy = redis.Redis.from_url(url).config_get(
            "maxmemory-policy").get("maxmemory-policy", "")
        if policy and policy != "noeviction":
            checks["broker"] = f"evicting: maxmemory-policy is {policy}"
            return False
        checks["broker"] = "ok"
    except Exception as exc:                                    # noqa: BLE001
        checks["broker"] = f"error: {exc.__class__.__name__}"
        return False
    return True


def readyz(_request):
    checks, ok = {}, True
    try:
        with connection.cursor() as c:
            c.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception as exc:                                    # noqa: BLE001
        checks["database"], ok = f"error: {exc.__class__.__name__}", False
    try:
        from django.core.cache import cache

        cache.set("readyz", 1, 5)
        checks["cache"] = "ok" if cache.get("readyz") == 1 else "degraded"
    except Exception as exc:                                    # noqa: BLE001
        checks["cache"], ok = f"error: {exc.__class__.__name__}", False

    ok = _broker(checks) and ok
    return JsonResponse({"status": "ok" if ok else "degraded", "checks": checks},
                        status=200 if ok else 503)
