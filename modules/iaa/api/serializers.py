"""IAA API serializers with explicit writable fields."""
from rest_framework import serializers
from modules.iaa.models import (Anomaly,ApprovalRule,ApprovalStep,AuditLog,AuditObservation,
 DashboardNotification,DepartmentBudget,FinancialRecord,FinancialYearPolicy,FinanceQuery,
 ObservationResponse,RoleAssignment,SupportingDocument)
class PageSerializer(serializers.Serializer):
    count=serializers.IntegerField()
    results=serializers.ListField(child=serializers.DictField())
class FinancialRecordWriteSerializer(serializers.Serializer):
    request_type=serializers.CharField(max_length=80); department=serializers.CharField(max_length=120)
    amount=serializers.DecimalField(max_digits=14,decimal_places=2,min_value=0)
    description=serializers.CharField(required=False,allow_blank=True,default="")
    financial_year=serializers.CharField(max_length=12,required=False,allow_blank=True)
    trip_start_date=serializers.DateField(required=False,allow_null=True)
    trip_end_date=serializers.DateField(required=False,allow_null=True)
    trip_purpose=serializers.CharField(max_length=240,required=False,allow_blank=True)
    trip_details=serializers.DictField(required=False,default=dict)
class SupportingDocumentInputSerializer(serializers.Serializer):
    name=serializers.CharField(max_length=255); storage_reference=serializers.CharField(max_length=700)
    content_type=serializers.CharField(max_length=120,required=False,allow_blank=True)
    size_bytes=serializers.IntegerField(required=False,allow_null=True,min_value=0)
class SupportingDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model=SupportingDocument; fields=("id","name","storage_reference","content_type","size_bytes","uploaded_by_id","created_at"); read_only_fields=fields
class ApprovalStepSerializer(serializers.ModelSerializer):
    record_id=serializers.IntegerField(read_only=True)
    class Meta:
        model=ApprovalStep; fields=("id","record_id","step_number","authority_role","assigned_user_id","status","due_at","decided_by_id","decided_role","decided_at","remarks"); read_only_fields=fields
class FinancialRecordSerializer(serializers.ModelSerializer):
    attachments=SupportingDocumentSerializer(many=True,read_only=True)
    approval_steps=ApprovalStepSerializer(many=True,read_only=True)
    class Meta:
        model=FinancialRecord
        fields=("id","record_kind","request_type","created_by_id","department","amount","description","status","financial_year","trip_start_date","trip_end_date","trip_purpose","trip_details","submitted_at","validated_at","recorded_at","current_approval_step","attachments","approval_steps","created_at","updated_at")
        read_only_fields=fields
class FinanceQuerySerializer(serializers.ModelSerializer):
    class Meta:
        model=FinanceQuery; fields=("id","record_id","asked_by_id","question","status","response","responded_by_id","responded_at","created_at"); read_only_fields=fields
class QueryInputSerializer(serializers.Serializer): question=serializers.CharField()
class QueryResponseInputSerializer(serializers.Serializer): response=serializers.CharField()
class FinanceValidationInputSerializer(serializers.Serializer):
    policy_passed=serializers.BooleanField(default=True); remarks=serializers.CharField(required=False,allow_blank=True,default="")
class ApprovalDecisionInputSerializer(serializers.Serializer):
    decision=serializers.ChoiceField(choices=("approve","reject")); remarks=serializers.CharField()
class AnomalyInputSerializer(serializers.Serializer):
    record_id=serializers.IntegerField(); category=serializers.CharField(max_length=80); details=serializers.CharField()
    severity=serializers.ChoiceField(choices=("low","medium","high","critical"),default="medium")
class AnomalySerializer(serializers.ModelSerializer):
    class Meta:
        model=Anomaly; fields=("id","record_id","category","severity","title","details","status","raised_by_id","resolver_role","resolver_user_id","resolution","resolved_at","created_at"); read_only_fields=fields
class AnomalyResolutionInputSerializer(serializers.Serializer):
    action=serializers.ChoiceField(choices=("resolve","escalate")); resolution=serializers.CharField()
class ObservationInputSerializer(serializers.Serializer):
    record_kind=serializers.ChoiceField(choices=FinancialRecord.RECORD_KINDS); record_id=serializers.IntegerField()
    title=serializers.CharField(max_length=200); details=serializers.CharField()
class ObservationResponseInputSerializer(serializers.Serializer):
    response_text=serializers.CharField()
    evidence_references=serializers.ListField(child=serializers.CharField(max_length=700),allow_empty=False)
class ObservationVerifyInputSerializer(serializers.Serializer):
    satisfactory=serializers.BooleanField(); remarks=serializers.CharField(required=False,allow_blank=True,default="")
class ObservationResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model=ObservationResponse; fields=("id","submitted_by_id","response_text","evidence_references","created_at"); read_only_fields=fields
class AuditObservationSerializer(serializers.ModelSerializer):
    responses=ObservationResponseSerializer(many=True,read_only=True)
    class Meta:
        model=AuditObservation; fields=("id","record_kind","record_id","department","title","details","raised_by_id","concerned_user_id","status","verified_by_id","verified_at","verification_remarks","closed_at","responses","created_at"); read_only_fields=fields
class RoleSwitchSerializer(serializers.Serializer): role=serializers.CharField(max_length=80)
class RoleAssignmentInputSerializer(serializers.Serializer):
    user_id=serializers.IntegerField(min_value=1); role=serializers.CharField(max_length=80); is_active=serializers.BooleanField(default=True)
class RoleAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model=RoleAssignment; fields=("id","user_id","role","assigned_by_id","is_active","created_at"); read_only_fields=fields
class ApprovalRuleInputSerializer(serializers.Serializer):
    record_kind=serializers.ChoiceField(choices=("", "expense_voucher","ta"),required=False,allow_blank=True)
    request_type=serializers.CharField(max_length=80,required=False,allow_blank=True,default="")
    department=serializers.CharField(max_length=120,required=False,allow_blank=True,default="")
    min_amount=serializers.DecimalField(max_digits=14,decimal_places=2,required=False,allow_null=True)
    max_amount=serializers.DecimalField(max_digits=14,decimal_places=2,required=False,allow_null=True)
    levels=serializers.ListField(child=serializers.DictField(),allow_empty=True)
    priority=serializers.IntegerField(min_value=0,default=100); is_active=serializers.BooleanField(default=True)
class ApprovalRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model=ApprovalRule; fields=("id","record_kind","request_type","department","min_amount","max_amount","levels","priority","is_active","created_at"); read_only_fields=fields
class FinancialYearPolicyInputSerializer(serializers.Serializer):
    financial_year=serializers.CharField(max_length=12); starts_on=serializers.DateField(); ends_on=serializers.DateField()
    settings=serializers.DictField(required=False,default=dict); is_active=serializers.BooleanField(default=True)
class FinancialYearPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model=FinancialYearPolicy; fields=("id","financial_year","starts_on","ends_on","settings","is_active"); read_only_fields=fields
class DepartmentBudgetInputSerializer(serializers.Serializer):
    department=serializers.CharField(max_length=120); financial_year=serializers.CharField(max_length=12)
    allocated=serializers.DecimalField(max_digits=16,decimal_places=2,min_value=0)
    spent=serializers.DecimalField(max_digits=16,decimal_places=2,min_value=0,required=False,default=0)
    committed=serializers.DecimalField(max_digits=16,decimal_places=2,min_value=0,required=False,default=0)
    is_active=serializers.BooleanField(default=True)
class DepartmentBudgetSerializer(serializers.ModelSerializer):
    class Meta:
        model=DepartmentBudget; fields=("id","department","financial_year","allocated","spent","committed","is_active","created_at"); read_only_fields=fields
class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model=AuditLog; fields=("id","actor_user_id","actor_role","action","resource_type","resource_id","from_status","to_status","details","created_at"); read_only_fields=fields
class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model=DashboardNotification; fields=("id","event_type","title","message","resource_type","resource_id","read_at","created_at"); read_only_fields=fields
