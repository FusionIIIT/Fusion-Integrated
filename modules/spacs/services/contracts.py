from __future__ import annotations

from dataclasses import dataclass
from typing import BinaryIO, Protocol, cast

from django.conf import settings
from django.utils.module_loading import import_string

from modules.spacs.models import Application, CatalogueVersion
from modules.spacs.services.errors import IntegrationUnavailableError


@dataclass(frozen=True)
class EligibilityResult:
    satisfied: bool
    failed_criterion_ids: tuple[str, ...] = ()


class EligibilityEvaluator(Protocol):
    def evaluate(
        self,
        *,
        user_id: int,
        application: Application,
        version: CatalogueVersion,
    ) -> EligibilityResult: ...


def configured_eligibility_evaluator() -> EligibilityEvaluator:
    provider_path = getattr(settings, "SPACS_ELIGIBILITY_EVALUATOR", "")
    if not provider_path:
        raise IntegrationUnavailableError("SPACS eligibility evaluation is not configured.")
    provider = import_string(provider_path)
    evaluator = provider() if isinstance(provider, type) else provider
    if not callable(getattr(evaluator, "evaluate", None)):
        raise IntegrationUnavailableError(
            "The configured SPACS eligibility evaluator does not implement its contract."
        )
    return cast("EligibilityEvaluator", evaluator)


class RoleHolderResolver(Protocol):
    def current_holder(self, role_name: str) -> int | None: ...


class DocumentStorage(Protocol):
    def store(
        self,
        *,
        filename: str,
        content_type: str,
        content: BinaryIO,
    ) -> str: ...

    def open(self, storage_reference: str) -> BinaryIO: ...

    def is_valid(
        self,
        *,
        storage_reference: str,
        requirement_id: str,
    ) -> bool: ...


def configured_document_storage() -> DocumentStorage:
    provider_path = getattr(settings, "SPACS_DOCUMENT_STORAGE", "")
    if not provider_path:
        raise IntegrationUnavailableError("Writable SPACS document storage is not configured.")
    provider = import_string(provider_path)
    storage = provider() if isinstance(provider, type) else provider
    if not all(
        callable(getattr(storage, method, None)) for method in ("store", "open", "is_valid")
    ):
        raise IntegrationUnavailableError(
            "The configured SPACS document storage does not implement "
            "the required storage contract."
        )
    return cast("DocumentStorage", storage)


def configured_role_holder_resolver() -> RoleHolderResolver:
    provider_path = getattr(settings, "SPACS_ROLE_HOLDER_RESOLVER", "")
    if not provider_path:
        raise IntegrationUnavailableError("SPACS role-holder resolution is not configured.")
    provider = import_string(provider_path)
    resolver = provider() if isinstance(provider, type) else provider
    if not callable(getattr(resolver, "current_holder", None)):
        raise IntegrationUnavailableError(
            "The configured SPACS role resolver does not implement its contract."
        )
    return cast("RoleHolderResolver", resolver)
