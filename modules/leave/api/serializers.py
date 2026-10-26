from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from modules.directory.models import UserRef
from modules.leave.domain import charge_by_year, eligible_for, starting_balance
from modules.leave.models import LeaveBalance, LeaveBalanceChange, LeaveRequest


class LeaveRequestSerializer(serializers.ModelSerializer):
    reason = serializers.CharField(trim_whitespace=True)

    class Meta:
        model = LeaveRequest
        fields = ("id", "employee_user_id", "leave_type", "start_date", "end_date",
                  "reason", "cl_period", "station_leave", "station_leave_details",
                  "chargeable_days", "status", "reviewed_by_user_id",
                  "reviewer_comment", "created_at")
        read_only_fields = ("id", "employee_user_id", "status", "reviewed_by_user_id",
                            "reviewer_comment", "chargeable_days", "created_at")

    def validate(self, attrs):
        user_id = self.context["request"].principal.user_id
        employee = UserRef.objects.filter(
            user_id=user_id, kind__in=("faculty", "staff"), is_active=True
        ).first()
        if employee is None:
            raise serializers.ValidationError("Only active faculty or staff may request leave.")
        if not eligible_for(employee.kind, attrs["leave_type"]):
            raise serializers.ValidationError({
                "leave_type": "This leave category is not available to this employee category."
            })
        request = LeaveRequest(employee_user_id=user_id, **attrs)
        try:
            request.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict if hasattr(exc, "message_dict")
                                              else exc.messages) from exc
        try:
            charges = charge_by_year(request.leave_type, request.start_date,
                                     request.end_date, request.cl_period)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict if hasattr(exc, "message_dict")
                                              else exc.messages) from exc
        pending = list(LeaveRequest.objects.filter(
            employee_user_id=user_id, leave_type=request.leave_type, status="pending"
        ).values_list("charge_by_year", flat=True))
        for year, amount in charges.items():
            balance = LeaveBalance.objects.filter(
                employee_user_id=user_id, leave_type=request.leave_type, year=int(year)
            ).first()
            available = (balance.available if balance else
                         starting_balance(employee.kind, request.leave_type))
            reserved = sum((Decimal(entry.get(year, "0")) for entry in pending),
                           start=Decimal("0"))
            if available - reserved < amount:
                raise serializers.ValidationError({
                    "leave_type": f"Insufficient {request.leave_type} balance for {year}."
                })
        self._charge_by_year = charges
        return attrs

    def create(self, validated_data):
        charges = self._charge_by_year
        validated_data["charge_by_year"] = {year: str(amount)
                                             for year, amount in charges.items()}
        validated_data["chargeable_days"] = sum(charges.values(), start=Decimal("0"))
        return super().create(validated_data)


class BalanceAdjustmentSerializer(serializers.Serializer):
    employee_user_id = serializers.IntegerField(min_value=1)
    leave_type = serializers.ChoiceField(choices=[code for code, _ in LeaveRequest.TYPE])
    year = serializers.IntegerField(min_value=2000, max_value=2200)
    amount = serializers.DecimalField(max_digits=7, decimal_places=2)
    note = serializers.CharField(max_length=300, trim_whitespace=True)

    def validate(self, attrs):
        employee = UserRef.objects.filter(user_id=attrs["employee_user_id"],
                                          kind__in=("faculty", "staff"),
                                          is_active=True).first()
        if employee is None or not eligible_for(employee.kind, attrs["leave_type"]):
            raise serializers.ValidationError("Employee or leave category is invalid.")
        if attrs["amount"] == 0:
            raise serializers.ValidationError({"amount": "Adjustment must be non-zero."})
        if not attrs["note"]:
            raise serializers.ValidationError({"note": "A reason is required."})
        return attrs


class CalendarDayInputSerializer(serializers.Serializer):
    date = serializers.DateField()
    is_closed = serializers.BooleanField(default=True)
    is_restricted_holiday = serializers.BooleanField(default=False)


class LeaveCalendarCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=120, trim_whitespace=True)
    days = CalendarDayInputSerializer(many=True)

    def validate(self, attrs):
        dates = [row["date"] for row in attrs["days"]]
        if len(set(dates)) != len(dates):
            raise serializers.ValidationError({"days": "Calendar dates must be unique."})
        if not attrs["title"]:
            raise serializers.ValidationError({"title": "A title is required."})
        return attrs


class LeaveBalanceChangeSerializer(serializers.ModelSerializer):
    leave_type = serializers.CharField(source="balance.leave_type", read_only=True)
    year = serializers.IntegerField(source="balance.year", read_only=True)
    leave_request_id = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta:
        model = LeaveBalanceChange
        fields = ("id", "leave_type", "year", "leave_request_id", "action",
                  "amount", "note", "actor_user_id", "created_at")
        read_only_fields = fields

