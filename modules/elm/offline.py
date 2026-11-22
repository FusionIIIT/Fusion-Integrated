from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied, ValidationError

from modules.elm.application import validate_request
from modules.elm.models import LeaveEvent, LeaveRequest
from modules.elm.validation import account, locked_employee
from modules.elm.workflows import emit


class OfflineMetadataSerializer(serializers.Serializer):
    employee = serializers.IntegerField(min_value=1)
    reference = serializers.CharField(allow_blank=False, trim_whitespace=True)
    evidence = serializers.CharField(allow_blank=False, trim_whitespace=True)
    unavailable_context = serializers.CharField(allow_blank=False, trim_whitespace=True)
    approved_at = serializers.DateTimeField()
    already_sanctioned = serializers.BooleanField()

    def validate_approved_at(self, value):
        if value > timezone.now():
            raise serializers.ValidationError("Future sanction")
        return value

    def validate_already_sanctioned(self, value):
        if not value:
            raise serializers.ValidationError("Existing sanction required")
        return value


@transaction.atomic
def synchronize(data, employee, principal, **metadata):
    if not principal.has_permission("elm.leave_records.manage"):
        raise PermissionDenied
    meta = OfflineMetadataSerializer(data={"employee": employee, **metadata})
    meta.is_valid(raise_exception=True)
    values = meta.validated_data
    user = locked_employee(employee)
    if LeaveEvent.objects.filter(
        employee=employee, action="OFFLINE_SYNCHRONIZED", details__reference=values["reference"]
    ).exists():
        raise ValidationError("Already synchronized")
    values["reference"]
    values["evidence"]
    values["unavailable_context"]
    approved_at = values["approved_at"]
    attrs = validate_request(data, employee, user.kind)
    row = account(employee, attrs["leave_type"], attrs["start_date"].year, user.kind)
    row.balance -= attrs["days"]
    row.last_updated = timezone.now()
    row.save()
    attrs["status"] = "APPROVED"
    attrs["approved_at"] = approved_at
    attrs["substitute_status"] = "ACCEPTED" if attrs.get("substitute") else "NONE"
    req = LeaveRequest.objects.create(**attrs)
    emit(
        req,
        principal.user_id,
        "OFFLINE_SYNCHRONIZED",
        delta=-req.days,
        reference=values["reference"],
        evidence=values["evidence"],
        unavailable_context=values["unavailable_context"],
        approved_at=values["approved_at"].isoformat(),
    )
    return req
