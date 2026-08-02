"""Request ids.

A user reads an id off an error toast; support greps that one id. That is the
entire purpose, and it is why the id also goes into the error envelope.
"""
import uuid
from contextvars import ContextVar

_request_id: ContextVar[str] = ContextVar("request_id", default="-")


def get_request_id() -> str:
    return _request_id.get()


class RequestIDMiddleware:
    HEADER = "HTTP_X_REQUEST_ID"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        rid = request.META.get(self.HEADER) or str(uuid.uuid4())
        token = _request_id.set(rid)
        try:
            response = self.get_response(request)
            response["X-Request-ID"] = rid
            return response
        finally:
            _request_id.reset(token)
