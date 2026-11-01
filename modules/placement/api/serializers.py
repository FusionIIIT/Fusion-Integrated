"""Serializers. Thin, and every write serializer is an explicit allow-list.

`fields = "__all__"` is never used here — it is exactly how `user_id`,
`status` or `cpi_at_apply` ends up writable by whoever posts the right JSON.
"""
from rest_framework import serializers

from modules.placement.models import (
    Announcement,
    Application,
    Company,
    CompanyContact,
    ConductIncident,
    InterviewRound,
    JobPosting,
    Offer,
    PlacementPolicy,
    PlacementRecord,
    PlacementRegistration,
    ProfileDocument,
    RoundParticipation,
)


# -- Companies -----------------------------------------------------------------
class CompanyContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyContact
        fields = ("id", "name", "designation", "email", "phone", "is_primary")


class CompanySerializer(serializers.ModelSerializer):
    contacts = CompanyContactSerializer(many=True, read_only=True)
    can_operate = serializers.BooleanField(read_only=True)

    class Meta:
        model = Company
        fields = ("id", "name", "slug", "sector", "sector_kind", "website",
                  "hq_city", "tier_rank", "is_marquee", "status",
                  "approval_status", "approval_note", "approved_at",
                  "can_operate", "contacts", "created_at")
        read_only_fields = fields


class CompanyBriefSerializer(serializers.ModelSerializer):
    """What a student sees. No approval trail, no internal notes."""

    class Meta:
        model = Company
        fields = ("id", "name", "slug", "sector", "sector_kind", "website",
                  "hq_city", "tier_rank", "is_marquee")
        read_only_fields = fields


class CompanyRegisterSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=160)
    sector = serializers.CharField(max_length=60, required=False, allow_blank=True)
    website = serializers.URLField(required=False, allow_blank=True)
    hq_city = serializers.CharField(max_length=80, required=False, allow_blank=True)
    contact_name = serializers.CharField(max_length=120, required=False,
                                         allow_blank=True)
    contact_email = serializers.EmailField(required=False, allow_blank=True)
    contact_phone = serializers.CharField(max_length=32, required=False,
                                          allow_blank=True)


class ApprovalSerializer(serializers.Serializer):
    note = serializers.CharField(max_length=300, required=False, allow_blank=True,
                                 default="")


# -- Postings ------------------------------------------------------------------
class JobPostingSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)

    class Meta:
        model = JobPosting
        fields = ("id", "title", "company_name", "season", "tier", "compensation_ctc", "min_cpi", "deadline", "status")


# -- Applications --------------------------------------------------------------
class ApplicationSerializer(serializers.ModelSerializer):
    posting_title = serializers.CharField(source='posting.title', read_only=True)

    class Meta:
        model = Application
        fields = ("id", "posting", "posting_title", "user_id", "status", "created_at")
