"""Serializers for RSPC.

Every write serializer uses an explicit allow-list of fields.
"""

from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers

from modules.rspc.models import (
    Project,
    ProjectBudgetHead,
    ProjectCoPI,
    ProjectFundTransaction,
    Proposal,
    ProposalReview,
)


class ProposalReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProposalReview
        fields = ("id", "reviewer_user_id", "reviewer_role", "action", "comments", "created_at")
        read_only_fields = fields


class ProposalSerializer(serializers.ModelSerializer):
    reviews = ProposalReviewSerializer(many=True, read_only=True)

    class Meta:
        model = Proposal
        fields = (
            "id",
            "user_id",
            "title",
            "proposal_type",
            "department",
            "funding_agency",
            "proposed_budget",
            "overhead_amount",
            "submission_deadline",
            "status",
            "summary",
            "reviews",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "user_id", "status", "created_at", "updated_at", "reviews")


class ProposalCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    proposal_type = serializers.ChoiceField(choices=["sponsored_research", "consultancy"])
    department = serializers.CharField(max_length=64)
    funding_agency = serializers.CharField(max_length=128)
    proposed_budget = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=Decimal("0.01")
    )
    overhead_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, default=Decimal("0.00")
    )
    submission_deadline = serializers.DateField(required=False, allow_null=True)
    summary = serializers.CharField(required=False, allow_blank=True, default="")


class ProposalReviewActionSerializer(serializers.Serializer):
    comments = serializers.CharField(required=False, allow_blank=True, default="")


class ProjectCoPISerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectCoPI
        fields = ("id", "user_id", "department", "share_percentage")
        read_only_fields = fields


class ProjectBudgetHeadSerializer(serializers.ModelSerializer):
    available_balance = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = ProjectBudgetHead
        fields = (
            "id",
            "head_type",
            "allocated_amount",
            "spent_amount",
            "committed_amount",
            "available_balance",
        )
        read_only_fields = fields


class ProjectFundTransactionSerializer(serializers.ModelSerializer):
    head_type = serializers.CharField(source="budget_head.head_type", read_only=True)

    class Meta:
        model = ProjectFundTransaction
        fields = (
            "id",
            "project_id",
            "budget_head_id",
            "head_type",
            "transaction_type",
            "amount",
            "reference_no",
            "description",
            "created_by_user_id",
            "created_at",
        )
        read_only_fields = fields


class ProjectSerializer(serializers.ModelSerializer):
    co_pis = ProjectCoPISerializer(many=True, read_only=True)
    budget_heads = ProjectBudgetHeadSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = (
            "id",
            "project_code",
            "project_type",
            "title",
            "user_id",
            "department",
            "funding_agency",
            "sanction_order_no",
            "sanction_date",
            "start_date",
            "end_date",
            "sanctioned_amount",
            "status",
            "co_pis",
            "budget_heads",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class ProjectCreateSerializer(serializers.Serializer):
    project_code = serializers.CharField(max_length=64)
    project_type = serializers.ChoiceField(choices=["sponsored", "consultancy"])
    title = serializers.CharField(max_length=255)
    department = serializers.CharField(max_length=64)
    funding_agency = serializers.CharField(max_length=128)
    sanction_order_no = serializers.CharField(max_length=128)
    sanction_date = serializers.DateField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    sanctioned_amount = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=Decimal("0.01")
    )
    co_pi_user_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, default=list
    )


class BudgetAllocationSerializer(serializers.Serializer):
    head_type = serializers.ChoiceField(choices=ProjectBudgetHead.HEAD_TYPES)
    allocated_amount = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=Decimal("0.01")
    )
    reference_no = serializers.CharField(max_length=128, required=False, default="")


class DisbursementSerializer(serializers.Serializer):
    head_type = serializers.CharField(max_length=32)
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
    reference_no = serializers.CharField(max_length=128)
    description = serializers.CharField(max_length=255, required=False, default="")


class ExtensionRequestSerializer(serializers.Serializer):
    requested_end_date = serializers.DateField()
    months_requested = serializers.IntegerField(min_value=1, max_value=24)
    justification = serializers.CharField()


class ExtensionReviewSerializer(serializers.Serializer):
    approved = serializers.BooleanField()
    comments = serializers.CharField(required=False, allow_blank=True, default="")
