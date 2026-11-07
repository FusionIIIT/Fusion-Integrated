from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from ..models import (
    PatentApplication, Inventor, ApplicationDocument,
    AttorneyAssignment, PatentabilityOpinion, Budget, Filing,
    OfficeAction, MaintenanceRecord, Appeal, ApplicationHistory
)


# --- Core Application Serializers ---

class PatentApplicationSerializer(serializers.ModelSerializer):
    """Read-only serializer for the core application record."""
    
    class Meta:
        model = PatentApplication
        fields = [
            'id', 'APPLICATION_NUMBER', 'title', 'abstract', 'description', 
            'claims', 'technical_domain', 'applicant_id', 'status', 
            'assigned_director_id', 'assigned_attorney_id', 'review_due_date', 
            'resubmission_deadline', 'latest_decision', 'latest_justification',
            'version_number', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'APPLICATION_NUMBER', 'status', 'assigned_director_id', 
            'assigned_attorney_id', 'review_due_date', 'resubmission_deadline',
            'latest_decision', 'latest_justification', 'version_number',
            'created_at', 'updated_at'
        ]

    def to_internal_representation(self, instance):
        return {
            'id': instance.id,
            'application_number': instance.APPLICATION_NUMBER,
            'title': instance.title,
            'abstract': instance.abstract,
            'description': instance.description,
            'claims': instance.claims,
            'technical_domain': instance.technical_domain,
            'applicant_id': instance.applicant_id,
            'status': instance.status,
            'assigned_director_id': instance.assigned_director_id,
            'assigned_attorney_id': instance.assigned_attorney_id,
            'review_due_date': instance.review_due_date,
            'resubmission_deadline': instance.resubmission_deadline,
            'latest_decision': instance.latest_decision,
            'latest_justification': instance.latest_justification,
            'version_number': instance.version_number,
        }


class ApplicationDetailSerializer(serializers.ModelSerializer):
    """Extended read serializer including inventors and documents."""
    
    inventors_count = serializers.IntegerField(source='inventors.count', read_only=True)
    documents_count = serializers.IntegerField(source='documents.count', read_only=True)

    class Meta:
        model = PatentApplication
        fields = [
            'id', 'application_number', 'title', 'abstract', 'description', 
            'claims', 'technical_domain', 'applicant_id', 'status', 
            'assigned_director_id', 'assigned_attorney_id', 'review_due_date', 
            'resubmission_deadline', 'latest_decision', 'latest_justification',
            'version_number', 'created_at', 'updated_at',
            'inventors_count', 'documents_count'
        ]


# --- Input Serializers for Actions ---

class SubmitApplicationSerializer(serializers.Serializer):
    """Input data for submitting a new application."""
    
    applicant_id = serializers.IntegerField(required=True, label=_('Applicant ID'))
    title = serializers.CharField(max_length=255, required=True, label=_('Title'))
    abstract = serializers.CharField(required=False, allow_blank=True, label=_('Abstract'))
    description = serializers.CharField(required=True, label=_('Description'))
    claims = serializers.CharField(required=True, label=_('Claims'))
    technical_domain = serializers.CharField(max_length=100, required=True, label=_('Technical Domain'))
    
    inventors = serializers.ListChild(
        child=serializers.DictField(
            child_keys=['user_id', 'name', 'email', 'contribution_percent', 'agreement_signed'],
            required=False
        ),
        required=True,
        label=_('Inventors')
    )
    
    documents = serializers.ListChild(
        child=serializers.DictField(
            child_keys=['file_name', 'content_type', 'size'],
            required=True
        ),
        required=True,
        label=_('Documents')
    )


class AssignDirectorSerializer(serializers.Serializer):
    """Input data for assigning a director."""
    
    director_id = serializers.IntegerField(required=True, label=_('Director ID'))
    # admin_id is implicitly the actor performing the action via request.principal


class ReviewApplicationSerializer(serializers.Serializer):
    """Input data for reviewing an application."""
    
    decision = serializers.ChoiceField(
        choices=['approve', 'reject', 'needs_revision'],
        required=True,
        label=_('Decision')
    )
    justification = serializers.CharField(min_length=50, required=True, label=_('Justification'))


class ResubmitApplicationSerializer(serializers.Serializer):
    """Input data for resubmitting an application."""
    
    changes = serializers.DictField(required=True, label=_('Changes'))
    response_to_feedback = serializers.CharField(required=True, label=_('Response to Feedback'))
    # applicant_id is implicitly the actor via request.principal


class WithdrawApplicationSerializer(serializers.Serializer):
    """Input data for withdrawing an application."""
    
    reason = serializers.CharField(required=True, label=_('Reason'))
    # applicant_id is implicitly the actor via request.principal


# --- Input Serializers for Appeals ---

class FileAppealSerializer(serializers.Serializer):
    """Input data for filing an appeal."""
    
    grounds = serializers.CharField(required=True, label=_('Grounds'))
    # applicant_id is implicitly the actor via request.principal


class DecideAppealSerializer(serializers.Serializer):
    """Input data for deciding an appeal."""
    
    outcome = serializers.ChoiceField(
        choices=['uphold_rejection', 'remand_for_amendment', 'modify_decision'],
        required=True,
        label=_('Outcome')
    )
    justification = serializers.CharField(required=True, label=_('Justification'))
    # director_id is implicitly the actor via request.principal


# --- Document and Other Models ---

class ApplicationDocumentSerializer(serializers.ModelSerializer):
    """Read-only serializer for application documents."""
    
    class Meta:
        model = ApplicationDocument
        fields = [
            'id', 'file_name', 'content_type', 'size', 'version', 
            'sensitivity', 'uploaded_by', 'archived', 'created_at'
        ]


class InventorSerializer(serializers.ModelSerializer):
    """Read-only serializer for inventors."""
    
    class Meta:
        model = Inventor
        fields = [
            'id', 'user_id', 'name', 'email', 'contribution_percent', 
            'agreement_signed', 'created_at'
        ]


class AttorneyAssignmentSerializer(serializers.ModelSerializer):
    """Read-only serializer for attorney assignments."""
    
    class Meta:
        model = AttorneyAssignment
        fields = [
            'id', 'attorney_id', 'status', 'decline_reason', 'created_at'
        ]


class PatentabilityOpinionSerializer(serializers.ModelSerializer):
    """Read-only serializer for patentability opinions."""
    
    class Meta:
        model = PatentabilityOpinion
        fields = [
            'id', 'attorney_id', 'novelty', 'non_obviousness', 'utility', 
            'recommendation', 'opinion_text', 'created_at'
        ]


class BudgetSerializer(serializers.ModelSerializer):
    """Read-only serializer for budgets."""
    
    class Meta:
        model = Budget
        fields = [
            'id', 'filing_fee', 'attorney_fee', 'administrative_cost', 
            'total', 'status', 'decided_by', 'justification', 'created_at'
        ]


class FilingSerializer(serializers.ModelSerializer):
    """Read-only serializer for external filings."""
    
    class Meta:
        model = Filing
        fields = [
            'id', 'patent_office', 'filing_number', 'filing_date', 
            'international', 'grant_number', 'grant_date', 'created_at'
        ]


class OfficeActionSerializer(serializers.ModelSerializer):
    """Read-only serializer for office actions."""
    
    class Meta:
        model = OfficeAction
        fields = [
            'id', 'received_date', 'response_due_date', 'description', 
            'response_text', 'status', 'created_at'
        ]


class MaintenanceRecordSerializer(serializers.ModelSerializer):
    """Read-only serializer for maintenance records."""
    
    class Meta:
        model = MaintenanceRecord
        fields = [
            'id', 'due_date', 'fee', 'decision', 'decided_by', 'created_at'
        ]


class AppealSerializer(serializers.ModelSerializer):
    """Read-only serializer for appeals."""
    
    class Meta:
        model = Appeal
        fields = [
            'id', 'grounds', 'status', 'decided_by', 'justification', 
            'created_at'
        ]


class ApplicationHistorySerializer(serializers.ModelSerializer):
    """Read-only serializer for application history."""
    
    class Meta:
        model = ApplicationHistory
        fields = [
            'id', 'actor_id', 'action', 'from_status', 'to_status', 
            'note', 'created_at'
        ]
