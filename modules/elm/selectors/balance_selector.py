from datetime import date
from decimal import Decimal

from modules.elm.models import LeaveBalance, LeaveBalanceEvent, LeavePolicy


class LeaveBalanceSelector:
    """Read one employee's annual leave account without creating records."""

    @staticmethod
    def for_user(user_id, employee_kind, year=None):
        year = year or date.today().year
        policies = LeavePolicy.objects.filter(is_active=True).order_by(
            "leave_type_code"
        )
        balances = {
            row.leave_type_code: row
            for row in LeaveBalance.objects.filter(user_id=user_id, year=year)
        }

        result = []
        for policy in policies:
            if policy.employee_kinds and employee_kind not in policy.employee_kinds:
                continue
            entitlement_by_kind = policy.annual_entitlement_by_kind or {}
            raw_entitlement = entitlement_by_kind.get(
                employee_kind, policy.annual_entitlement
            )
            entitlement = (
                Decimal(str(raw_entitlement))
                if raw_entitlement is not None
                else Decimal("0")
            )
            account = balances.get(policy.leave_type_code)
            if account is None:
                opening = Decimal("0")
                credit = entitlement
                if policy.carries_forward:
                    previous = LeaveBalance.objects.filter(
                        user_id=user_id,
                        leave_type_code=policy.leave_type_code,
                        year=year - 1,
                    ).first()
                    if previous is not None:
                        opening = max(Decimal("0"), previous.available_days)
            else:
                opening = Decimal(str(account.opening_balance))
                credit = Decimal(str(account.annual_credit))
            used = Decimal(str(account.used_days)) if account else Decimal("0")
            reserved = Decimal(str(account.reserved_days)) if account else Decimal("0")
            result.append({
                "leave_type_code": policy.leave_type_code,
                "year": year,
                "annual_entitlement": entitlement,
                "opening_balance": opening,
                "annual_credit": credit,
                "used_days": used,
                "reserved_days": reserved,
                "available_days": opening + credit - used - reserved,
                "carries_forward": policy.carries_forward,
            })
        return result

    @staticmethod
    def history_for_user(user_id, leave_type_code=None):
        events = LeaveBalanceEvent.objects.filter(
            balance__user_id=user_id
        ).select_related("balance")
        if leave_type_code:
            events = events.filter(balance__leave_type_code=leave_type_code)
        return events.order_by("-created_at", "-id")
