"""PMS write routes use the principal-aware configured throttle."""

from django.conf import settings
from django.core.cache import cache
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate

from core.api.throttling import PrincipalScopedThrottle
from modules.pms.api.errors import PmsWriteAPIView
from modules.pms.api.urls import urlpatterns


def test_every_pms_write_route_declares_a_throttle_scope():
    for route in urlpatterns:
        view = getattr(route.callback, "cls", None)
        if view and any(getattr(view, method, None) for method in ("post", "put", "patch", "delete")):
            assert view.throttle_scope == "pms_write", view.__name__


def test_pms_write_base_returns_429_after_configured_write_limit(monkeypatch):
    class ProbeWriteView(PmsWriteAPIView):
        authentication_classes = []
        permission_classes = []

        def post(self, request):
            return Response(status=201)

    assert settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["pms_write"] == "60/min"
    monkeypatch.setattr(
        PrincipalScopedThrottle,
        "THROTTLE_RATES",
        {**PrincipalScopedThrottle.THROTTLE_RATES, "pms_write": "1/min"},
    )
    factory = APIRequestFactory()

    cache.clear()
    first_request = factory.post("/api/v1/pms/probe/")
    second_request = factory.post("/api/v1/pms/probe/")
    force_authenticate(first_request, user=object())
    force_authenticate(second_request, user=object())
    first = ProbeWriteView.as_view()(first_request)
    second = ProbeWriteView.as_view()(second_request)
    cache.clear()

    assert first.status_code == 201
    assert second.status_code == 429
