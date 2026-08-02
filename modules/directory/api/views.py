from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError
from modules.directory import contracts
from modules.directory.api.serializers import UserSearchResultSerializer

MAX_LIMIT = 100


@extend_schema(responses=UserSearchResultSerializer)
class UserSearchView(APIView):
    """Type-ahead over the local projection. Read-only by construction —
    directory data is owned by IAM and edited there."""

    def get(self, request):
        raw = request.query_params.get("limit", 25)
        try:
            limit = min(int(raw), MAX_LIMIT)
        except (TypeError, ValueError) as exc:
            raise BadRequestError("limit must be a number.",
                                  code="invalid_filter") from exc

        rows = contracts.search(
            q=request.query_params.get("q", ""),
            kind=request.query_params.get("kind"),
            limit=max(limit, 1),
        )
        return Response({"results": [r.__dict__ for r in rows]})
