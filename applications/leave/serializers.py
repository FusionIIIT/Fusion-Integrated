from datetime import datetime, date
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import LeaveType, LeaveBalance, LeaveRequest

User = get_user_model()


class LeaveTypeSerializer(serializers.ModelSerializer):
    """Serializer for leave types."""
    class Meta:
        model = LeaveType
        fields = '__all__'


class LeaveBalanceSerializer(serializers.ModelSerializer):
    """Read-only serializer for leave balance inquiry."""
    available_days = serializers.ReadOnlyField()

    class Meta:
        model = LeaveBalance
        fields = [
            'id', 'user', 'leave_type', 'total_days',
            'consumed_days', 'pending_days', 'available_days'
        ]
        read_only_fields = ['available_days']


class LeaveRequestSerializer(serializers.ModelSerializer):
    """Serializer for leave request creation and validation."""

    class Meta:
        model = LeaveRequest
        fields = [
            'id', 'user', 'leave_type', 'start_date', 'end_date',
            'total_days', 'reason', 'station_leave', 'address_during_leave',
            'contact_during_leave', 'substitute_name', 'status', 'remarks',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'status', 'remarks', 'created_at', 'updated_at']

    def validate(self, data):
        """Validate leave request before saving."""
        # 1. Resolve user from request context, input data, or existing instance
        user = None
        if self.context and 'request' in self.context:
            req = self.context['request']
            user = getattr(req, 'user', None) or getattr(req, '_force_auth_user', None)
        elif 'user' in data:
            user = data['user']
        elif self.initial_data and 'user' in self.initial_data:
            try:
                user = User.objects.get(pk=self.initial_data['user'])
            except (User.DoesNotExist, TypeError, ValueError):
                user = None
        elif self.instance:
            user = self.instance.user

        if not user or not getattr(user, 'is_authenticated', False):
            raise serializers.ValidationError({
                'user': "Authenticated user is required to validate leave requests."
            })

        leave_type = data.get('leave_type') or (self.instance.leave_type if self.instance else None)
        if not leave_type:
            raise serializers.ValidationError({'leave_type': "Leave type is required."})

        start_date = data.get('start_date')
        end_date = data.get('end_date')

        # Convert date strings if passed as raw text
        if isinstance(start_date, str):
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            except ValueError:
                raise serializers.ValidationError({'start_date': "Invalid date format. Use YYYY-MM-DD."})

        if isinstance(end_date, str):
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                raise serializers.ValidationError({'end_date': "Invalid date format. Use YYYY-MM-DD."})

        # 2. Start date <= end date validation
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError({
                'start_date': "Start date must be on or before end date."
            })

        # 3. Check for overlapping leave periods
        if start_date and end_date:
            active_requests = LeaveRequest.objects.filter(
                user=user,
                status__in=['submitted', 'unit_head_review', 'establishment_review',
                            'final_decision_pending', 'approved', 'PENDING'],
                start_date__lte=end_date,
                end_date__gte=start_date
            )
            if self.instance and self.instance.pk:
                active_requests = active_requests.exclude(pk=self.instance.pk)

            if active_requests.exists():
                raise serializers.ValidationError({
                    'end_date': "This leave period overlaps with an existing approved or pending request."
                })

        # 4. Check quota balance availability
        total_days = data.get('total_days')
        if total_days is not None:
            try:
                balance = LeaveBalance.objects.get(user=user, leave_type=leave_type)
                if not balance.can_grant_leave(float(total_days)):
                    raise serializers.ValidationError({
                        'total_days': f"Insufficient {leave_type.name} balance. Available: {balance.available_days} days."
                    })
            except LeaveBalance.DoesNotExist:
                pass

        return data


class LeaveActionSerializer(serializers.Serializer):
    """Serializer for reviewer actions (approve/reject/forward)."""

    action = serializers.ChoiceField(
        choices=['approve', 'reject', 'forward'],
        help_text="Action to take: approve, reject, or forward"
    )
    remarks = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
        help_text="Remarks for the action. Required for reject actions."
    )

    def validate(self, data):
        if data.get('action') == 'reject' and not data.get('remarks'):
            raise serializers.ValidationError({'remarks': "Remarks are required when rejecting a request."})
        return data


class LeavePermissionCheckMixin:
    """Mixin to check Fusion IAM permissions for reviewer actions."""

    def check_permission(self, user, permission_code):
        request = getattr(self, 'request', None) or getattr(self, 'context', {}).get('request', None)
        if not request or not getattr(request, 'user', None) or not request.user.is_authenticated:
            return False

        try:
            from fusion_auth.permissions import HasPermission
            return HasPermission(permission_code)(request.user)
        except Exception:
            return user.is_authenticated
