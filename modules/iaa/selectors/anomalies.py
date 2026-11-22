from django.db.models import QuerySet

from modules.iaa.models import Anomaly
from modules.iaa.selectors.scoping import scope_anomalies


def get_anomalies(principal, status: str | None = None) -> QuerySet[Anomaly]:
    qs = scope_anomalies(Anomaly.objects.all(), principal)
    if status:
        qs = qs.filter(status=status)
    return qs


def get_anomaly_by_id(principal, anomaly_id: int) -> Anomaly | None:
    return get_anomalies(principal).filter(id=anomaly_id).first()
