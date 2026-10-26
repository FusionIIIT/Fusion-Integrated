"""Leave account ledger. Balances change only through post() (SRS-EL-053, 101)."""
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

from modules.elm.models import LeaveAccount, LeaveRequest, LeaveTransaction

T = LeaveTransaction.Kind


class AccountError(Exception):
    pass


def _locked_account(user_id: int, year: int, leave_type: str) -> LeaveAccount:
    acct, _ = LeaveAccount.objects.get_or_create(
        user_id=user_id, year=year, leave_type=leave_type)
    return LeaveAccount.objects.select_for_update().get(pk=acct.pk)


@transaction.atomic
def post(user_id: int, year: int, leave_type: str, kind: str, amount,
         request: LeaveRequest | None = None, note: str = "") -> LeaveAccount:
    """Append one ledger row and move the balance. Never lets a balance go negative."""
    amount = Decimal(amount)
    acct = _locked_account(user_id, year, leave_type)
    new_balance = acct.balance + amount
    if new_balance < 0:
        raise AccountError("Posting would make the balance negative.")
    LeaveTransaction.objects.create(
        account=acct, kind=kind, amount=amount, request=request, note=note)
    acct.balance = new_balance
    acct.save(update_fields=["balance", "updated_at"])
    return acct


def entitlements_for(employee_kind: str, params: dict) -> dict:
    """BR-EL-002..009: what one employee is credited each year.

    Faculty get VL (and receive EL only through year-end conversion);
    everyone else gets 30 EL.
    """
    ent = {t: params[t] for t in ("CL", "RH", "SCL", "COL")}
    if employee_kind == "faculty":
        ent["VL"] = params["VL"]
    else:
        ent["EL"] = params["EL"]
    return ent


@transaction.atomic
def credit_annual(user_id: int, year: int, employee_kind: str, params: dict) -> list[str]:
    """Idempotent: a type already credited for the year is skipped."""
    credited = []
    for leave_type, amount in entitlements_for(employee_kind, params).items():
        already = LeaveTransaction.objects.filter(
            account__user_id=user_id, account__year=year,
            account__leave_type=leave_type, kind=T.CREDIT).exists()
        if already:
            continue
        post(user_id, year, leave_type, T.CREDIT, amount, note=f"Annual credit {year}")
        credited.append(leave_type)
    return credited


def _net_debited(request: LeaveRequest) -> Decimal:
    rows = LeaveTransaction.objects.filter(request=request)
    debit = rows.filter(kind=T.DEBIT).aggregate(s=Sum("amount"))["s"] or Decimal("0")
    restored = rows.filter(kind=T.RESTORE).aggregate(s=Sum("amount"))["s"] or Decimal("0")
    return -debit - restored


@transaction.atomic
def debit_for_request(request: LeaveRequest) -> LeaveAccount:
    """Post the leave effect after final approval (SRS-EL-053).

    Extensions are their own request, so only the incremental days are posted (SRS-EL-075).
    """
    if request.status != LeaveRequest.Status.APPROVED:
        raise AccountError("Only an approved request can be debited.")
    if LeaveTransaction.objects.filter(request=request, kind=T.DEBIT).exists():
        raise AccountError("This request has already been debited.")
    return post(request.applicant_id, request.start_date.year, request.leave_type,
                T.DEBIT, -request.days, request=request, note="Approved leave")


@transaction.atomic
def reverse_for_request(request: LeaveRequest) -> LeaveAccount:
    """Approved-leave cancellation: give back whatever is still debited (SRS-EL-066)."""
    outstanding = _net_debited(request)
    if outstanding <= 0:
        raise AccountError("Nothing to reverse for this request.")
    return post(request.applicant_id, request.start_date.year, request.leave_type,
                T.RESTORE, outstanding, request=request, note="Cancellation reversal")


@transaction.atomic
def restore_unused(request: LeaveRequest, unused_days) -> LeaveAccount:
    """Verified early resumption (SRS-EL-083). Never more than is still debited."""
    unused_days = Decimal(unused_days)
    if unused_days <= 0:
        raise AccountError("Unused days must be positive.")
    if unused_days > _net_debited(request):
        raise AccountError("Cannot restore more than was debited.")
    return post(request.applicant_id, request.start_date.year, request.leave_type,
                T.RESTORE, unused_days, request=request, note="Early resumption")
