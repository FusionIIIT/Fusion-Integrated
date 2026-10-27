from rest_framework import serializers
from .models import LeaveType, LeaveBalance, LeaveRequest


class LeaveTypeSerializer(serializers.ModelSerializer):
    """Read-only serializer for leave type information."""
    
    class Meta:
        model = LeaveType
        fields = ['id', 'name', 'annual_quota', 'carry_forward', 
                  'requires_medical_evidence', 'description']
        read_only_fields = ['id', 'annual_quota', 'carry_forward', 
                           'requires_medical_evidence', 'description']


class LeaveBalanceSerializer(serializers.ModelSerializer):
    """Read-only serializer for leave balance inquiry."""
    
    available_days = serializers.ReadOnlyField()
    
    class Meta:
        model = LeaveBalance
        fields = ['id', 'user', 'leave_type', 'total_days', 
                  'consumed_days', 'pending_days', 'available_days']
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
        read_only_fields = ['user', 'leave_type', 'start_date', 'end_date', 
                           'total_days', 'station_leave', 'address_during_leave',
                           'contact_during_leave', 'substitute_name', 'status',
                           'remarks', 'created_at', 'updated_at']
    
    def validate(self, data):
        """Validate leave request before saving."""
        user = data['user']
        leave_type = data['leave_type']
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        
        # Handle date string inputs - convert to date objects for comparison
        from datetime import datetime
        if isinstance(start_date_str, str):
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                raise serializers.ValidationError({
                    'start_date': "Invalid date format. Use YYYY-MM-DD."
                })
        else:
            start_date = start_date_str
        
        if isinstance(end_date_str, str):
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                raise serializers.ValidationError({
                    'end_date': "Invalid date format. Use YYYY-MM-DD."
                })
        else:
            end_date = end_date_str
        
        # Ensure start date is not after end date
        if start_date > end_date:
            raise serializers.ValidationError({
                'start_date': "Start date must be on or before end date."
            })
        
        # Check for overlapping leave periods
        active_requests = LeaveRequest.objects.filter(
            user=user,
            status__in=['submitted', 'unit_head_review', 'establishment_review', 
                        'final_decision_pending', 'approved'],
            start_date__lte=end_date,
            end_date__gte=start_date
        ).exclude(pk=data.get('id'))
        
        if active_requests.exists():
            raise serializers.ValidationError({
                'end_date': "This leave period overlaps with an existing approved or pending request."
            })
        
        # Check balance availability
        try:
            balance = LeaveBalance.objects.get(user=user, leave_type=leave_type)
            if not balance.can_grant_leave(float(data['total_days'])):
                raise serializers.ValidationError({
                    'total_days': f"Insufficient {leave_type.name} balance. Available: {balance.available_days} days."
                })
        except LeaveBalance.DoesNotExist:
            pass  # No balance record yet, will be created on save
        
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
        """Validate reviewer action."""
        if data['action'] == 'reject' and not data.get('remarks'):
            raise serializers.ValidationError({
                'remarks': "Remarks are required when rejecting a leave request."
            })
        
        return data


class LeavePermissionCheckMixin:
    """Mixin to check Fusion IAM permissions for reviewer actions."""
    
    def check_permission(self, user, permission_code):
        """Check if user has the required permission."""
        from rest_framework.permissions import IsAuthenticated
        from fusion_auth.permissions import HasPermission
        
        # Check if user is authenticated
        if not self.context.get('request'):
            return False
        
        request = self.context['request']
        
        # Use Fusion IAM permission checking
        try:
            has_perm = HasPermission(permission_code)(request.user)
            return has_perm
        except Exception:
            # Fallback to basic check if Fusion auth not available
            return user.is_authenticated
    
    def get_required_permission(self, action):
        """Get required permission code for an action."""
        permissions = {
            'approve': 'leave_request.approve',
            'reject': 'leave_request.reject',
            'forward': 'leave_request.forward',
            'cancel': 'leave_request.cancel',
            'view': 'leave_request.view'
        }
        return permissions.get(action, 'leave_request.view')
