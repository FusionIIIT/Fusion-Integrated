"""Request-scoped idempotency for CMS create/mutation POSTs."""

from __future__ import annotations

import hashlib
import json
import re

from django.db import IntegrityError, transaction
from rest_framework.response import Response

from core.api.exceptions import BadRequestError, ConflictError
from modules.complaints.models import IdempotencyRecord

_KEY = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def post_once(request, operation):
    key = request.headers.get("Idempotency-Key", "").strip()
    if not _KEY.fullmatch(key):
        raise BadRequestError(
            "A valid Idempotency-Key header is required.", code="idempotency_key_required"
        )
    raw = json.dumps(
        {"method": request.method, "path": request.path, "data": _normalize(request.data)},
        sort_keys=True,
        default=str,
        separators=(",", ":"),
    )
    fingerprint = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    user_id = request.principal.user_id
    with transaction.atomic():
        try:
            with transaction.atomic():
                record = IdempotencyRecord.objects.create(
                    user_id=user_id, key=key, request_fingerprint=fingerprint
                )
        except IntegrityError:
            record = (
                IdempotencyRecord.objects.select_for_update()
                .filter(user_id=user_id, key=key)
                .first()
            )
            if record is None:
                raise ConflictError(
                    "The request is already being processed.", code="idempotency_in_progress"
                ) from None
            if record.request_fingerprint != fingerprint:
                raise ConflictError(
                    "This Idempotency-Key was already used for a different request.",
                    code="idempotency_key_reused",
                ) from None
            if record.response_body is None or record.response_status is None:
                raise ConflictError(
                    "The request is already being processed.", code="idempotency_in_progress"
                ) from None
            return Response(record.response_body, status=record.response_status)
        data, response_status = operation()
        record.response_body = data
        record.response_status = response_status
        record.save(update_fields=("response_body", "response_status", "updated_at"))
    return Response(data, status=response_status)


def _normalize(value):
    if hasattr(value, "getlist"):
        return {
            key: [_normalize(item) for item in value.getlist(key)] for key in sorted(value.keys())
        }
    if isinstance(value, dict):
        return {str(key): _normalize(item) for key, item in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    if hasattr(value, "chunks") and hasattr(value, "size") and hasattr(value, "name"):
        position = value.tell()
        digest = hashlib.sha256()
        for chunk in value.chunks():
            digest.update(chunk)
        value.seek(position)
        return {"upload": value.name, "size": value.size, "sha256": digest.hexdigest()}
    return value
