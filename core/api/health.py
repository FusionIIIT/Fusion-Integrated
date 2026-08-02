from django.db import connection
from django.http import JsonResponse


def healthz(_request):
    """Liveness. Checks nothing external on purpose — a probe that fails when
    Postgres blips would restart a healthy process during an incident."""
    return JsonResponse({"status": "ok"})


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
    return JsonResponse({"status": "ok" if ok else "degraded", "checks": checks},
                        status=200 if ok else 503)
