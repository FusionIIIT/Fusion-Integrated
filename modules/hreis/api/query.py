"""Boundary validation for all HR-EIS cursor-paginated list endpoints."""

from rest_framework.exceptions import NotFound

from core.api.exceptions import BadRequestError


class ValidatedListQueryMixin:

    def get(self, request, *args, **kwargs):
        params = request.query_params
        for name in params:
            if name not in {"cursor", "limit"}:
                raise BadRequestError(
                    f"Unsupported query parameter '{name}'. Use only 'limit' and 'cursor'.",
                    code="invalid_list_query",
                )
            if len(params.getlist(name)) != 1:
                raise BadRequestError(
                    f"Supply '{name}' only once and retry.",
                    code="invalid_list_query",
                )

        if "limit" in params:
            value = params["limit"]
            if not value.isascii() or not value.isdecimal() or len(value) > 3:
                raise BadRequestError(
                    "The list limit must be a whole number from 1 to 100. Correct it and retry.",
                    code="invalid_list_limit",
                )
            if not 1 <= int(value) <= 100:
                raise BadRequestError(
                    "The list limit must be between 1 and 100. Correct it and retry.",
                    code="invalid_list_limit",
                )

        if "cursor" in params and not 1 <= len(params["cursor"]) <= 2048:
            raise BadRequestError(
                "The pagination cursor is invalid. Reload the first page and retry.",
                code="invalid_list_cursor",
            )
        try:
            return super().get(request, *args, **kwargs)
        except NotFound as exc:
            if "cursor" not in params:
                raise
            raise BadRequestError(
                "The pagination cursor is invalid or expired. Reload the first page and retry.",
                code="invalid_list_cursor",
            ) from exc
