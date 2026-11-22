"""Security threshold and failed login monitoring service (BR-SA-024)."""

from django.core.cache import cache

from modules.superadmin.selectors.system_config import get_parameter_value
from modules.superadmin.services.audit import log_audit_event


def record_failed_login(user_id: int, ip_address: str | None = None) -> tuple[int, bool]:
    # BR-SA-024: Track failed logins against security threshold.
    cache_key = f"sa_failed_login_{user_id}"
    count = cache.get(cache_key, 0) + 1
    cache.set(cache_key, count, timeout=3600)

    threshold = int(get_parameter_value("FAILED_LOGIN_THRESHOLD", 5))
    alert_triggered = False

    if count >= threshold:
        alert_triggered = True
        log_audit_event(
            event_type="SECURITY_ALERT_FAILED_LOGINS",
            actor_user_id=user_id,
            target_entity="UserAccountRecord",
            target_id=str(user_id),
            ip_address=ip_address,
            action_details={"consecutive_failed_logins": count, "threshold": threshold},
        )

    return count, alert_triggered


def reset_failed_logins(user_id: int) -> None:
    cache_key = f"sa_failed_login_{user_id}"
    cache.delete(cache_key)
