"""Shared view plumbing: the two gates, people's names, query parsing and schema examples."""
from __future__ import annotations

import dataclasses

from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, NotFoundError
from core.api.pagination import CursorPagination
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.directory import contracts as directory
from modules.pms import registry
from modules.pms.domain.roles import acting_permissions

MODULE = HasModuleGrant("pms")


def gate(*codes: str) -> list:
    """BR-PMS-126: the module grant first, then the permission."""
    return [MODULE, HasPermission(*codes)]


def names(user_ids) -> dict[int, str]:
    """One directory call for every person a response names."""
    ids = sorted({u for u in user_ids if u is not None})
    people = directory.get_users(ids) if ids else {}
    return {u: people[u].display_name for u in ids if u in people}


def int_param(params, name: str) -> int | None:
    raw = params.get(name)
    if raw in (None, ""):
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise BadRequestError(f"{name} must be a whole number.", code="invalid_filter") from exc
    if value < 1:
        raise BadRequestError(f"{name} must be positive.", code="invalid_filter")
    return value


def found(obj, what: str = "record"):
    if obj is None:
        raise NotFoundError(f"No such {what}.", code="not_found")
    return obj


class Pagination(CursorPagination):
    ordering = "-id"


def schema(summary: str, *, request=None, response=None, example_in=None, example_out=None,
           status: int = 200, parameters=None):
    examples = []
    if example_in is not None:
        examples.append(OpenApiExample("request", value=example_in, request_only=True))
    if example_out is not None:
        examples.append(OpenApiExample("response", value=example_out, response_only=True,
                                       status_codes=[str(status)]))
    return extend_schema(summary=summary, tags=["pms"], request=request,
                         responses={status: response}, examples=examples,
                         parameters=parameters)


def narrow(principal):
    """The IAM sends every held role's permissions; PMS acts on the acting role's only."""
    if principal is None:
        return None
    return dataclasses.replace(principal, permissions=acting_permissions(
        principal.permissions, principal.active_role, principal.kind, registry.ROLE_GRANTS))


class PmsView(APIView):
    throttle_scope = None

    def perform_authentication(self, request):
        super().perform_authentication(request)
        if getattr(request, "principal", None) is not None:
            request.principal = narrow(request.principal)

    @property
    def actor(self):
        return self.request.principal


class WriteView(PmsView):
    """Writes are throttled; reads on the same path are not."""

    throttle_scope = "pms_write"

    def get_throttles(self):
        return [] if self.request.method in ("GET", "HEAD", "OPTIONS") else super().get_throttles()
