"""Read-only, batched IAA contract. Callers must apply their own authorization."""

from collections.abc import Sequence

from modules.iaa.models import FinancialRequest


def get_record_statuses(request_ids: Sequence[int]) -> dict[int, str]:
    return dict(FinancialRequest.objects.filter(pk__in=request_ids).values_list("id", "status"))
