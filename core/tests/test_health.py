"""Readiness, and the one broker misconfiguration that is otherwise silent."""
import pytest
from django.test import Client

pytestmark = pytest.mark.django_db


class FakeRedis:
    def __init__(self, policy):
        self.policy = policy

    @classmethod
    def make(cls, policy):
        return lambda url: cls(policy)

    def config_get(self, _key):
        return {"maxmemory-policy": self.policy}


def _with_broker(monkeypatch, settings, url, policy=None, boom=False):
    settings.CELERY_BROKER_URL = url
    import redis

    if boom:
        def explode(_url):
            raise redis.ConnectionError("refused")
        monkeypatch.setattr(redis.Redis, "from_url", staticmethod(explode))
    elif policy is not None:
        monkeypatch.setattr(redis.Redis, "from_url",
                            staticmethod(FakeRedis.make(policy)))


def test_liveness_touches_nothing_external():
    assert Client().get("/healthz").json() == {"status": "ok"}


def test_a_memory_broker_is_not_a_failure(settings):
    """Normal in dev and tests; prod refuses to boot without a real broker."""
    settings.CELERY_BROKER_URL = "memory://"
    body = Client().get("/readyz").json()
    assert body["status"] == "ok"
    assert body["checks"]["broker"].startswith("not redis")


def test_a_noeviction_broker_is_ready(monkeypatch, settings):
    _with_broker(monkeypatch, settings, "redis://127.0.0.1:6380/0", "noeviction")
    r = Client().get("/readyz")
    assert r.status_code == 200
    assert r.json()["checks"]["broker"] == "ok"


def test_an_evicting_broker_is_reported_as_not_ready(monkeypatch, settings):
    """An LRU broker drops queued tasks with no error: no send, no expiry, no
    trace. Readiness is the only place that can say so."""
    _with_broker(monkeypatch, settings, "redis://127.0.0.1:6380/0", "allkeys-lru")
    r = Client().get("/readyz")
    assert r.status_code == 503
    assert "allkeys-lru" in r.json()["checks"]["broker"]


def test_an_unreachable_broker_is_reported(monkeypatch, settings):
    _with_broker(monkeypatch, settings, "redis://127.0.0.1:6380/0", boom=True)
    r = Client().get("/readyz")
    assert r.status_code == 503
    assert r.json()["checks"]["broker"].startswith("error:")
