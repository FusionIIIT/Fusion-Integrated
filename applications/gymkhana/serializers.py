"""Gymkhana serializers.

ModelSerializers keep user-submitted fields writable.
Audit/immutable fields are read_only_fields = ['id', 'user', 'status', 'created_at', 'updated_at'].
User context is resolved safely via self.context.get('request') or data.get().
"""
from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from .models import (
    Club,
    ClubBudgetRequest,
    ClubEvent,
    ClubEventReport,
    ClubMembership,
    ClubSession,
    GymkhanaWorkflowHistory,
    PollChoice,
    PollVote,
    Venue,
    VotingPoll,
)


# ---------------------------------------------------------------------------
# Venue
# ---------------------------------------------------------------------------

class VenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Venue
        fields = ['id', 'name', 'capacity', 'description']
        read_only_fields = ['id']


# ---------------------------------------------------------------------------
# Club
# ---------------------------------------------------------------------------

class ClubSerializer(serializers.ModelSerializer):
    class Meta:
        model = Club
        fields = [
            'id', 'name', 'description', 'category',
            'coordinator', 'co_coordinator', 'faculty_councillor',
            'status', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'status', 'created_at', 'updated_at']

    def validate_category(self, value):
        allowed = {'technical', 'sports', 'cultural'}
        if value not in allowed:
            raise serializers.ValidationError(
                f"Category must be one of: {', '.join(sorted(allowed))}."
            )
        return value


# ---------------------------------------------------------------------------
# Club Membership
# ---------------------------------------------------------------------------

class ClubMembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClubMembership
        fields = [
            'id', 'club', 'student', 'achievements',
            'status', 'remarks', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'student', 'status', 'remarks', 'created_at', 'updated_at']

    def validate(self, data):
        # Safely resolve the applicant
        request = self.context.get('request')
        user = getattr(request, 'user', None) if request else data.get('user')

        club = data.get('club') or (self.instance.club if self.instance else None)

        # BR-GYM-007: only confirmed clubs accept applications
        if club and club.status != 'confirmed':
            raise serializers.ValidationError(
                {'club': "Membership applications are only allowed for confirmed clubs."}
            )

        # BR-GYM-009: no duplicate same-club application
        if club and user:
            qs = ClubMembership.objects.filter(club=club, student=user)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {'club': "You already have an application for this club."}
                )

        return data


# ---------------------------------------------------------------------------
# Club Session
# ---------------------------------------------------------------------------

class ClubSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClubSession
        fields = [
            'id', 'club', 'venue', 'date', 'start_time', 'end_time',
            'description', 'poster', 'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']

    def validate(self, data):
        start_time = data.get('start_time') or (self.instance.start_time if self.instance else None)
        end_time = data.get('end_time') or (self.instance.end_time if self.instance else None)

        # BR-GYM-005: start_time must be before end_time
        if start_time and end_time and start_time >= end_time:
            raise serializers.ValidationError(
                {'start_time': "Session start time must be before end time."}
            )
        return data


# ---------------------------------------------------------------------------
# Club Event
# ---------------------------------------------------------------------------

class ClubEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClubEvent
        fields = [
            'id', 'club', 'name', 'venue', 'date', 'start_time', 'end_time',
            'description', 'poster', 'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']

    def validate(self, data):
        start_time = data.get('start_time') or (self.instance.start_time if self.instance else None)
        end_time = data.get('end_time') or (self.instance.end_time if self.instance else None)

        # BR-GYM-005: start_time must be before end_time
        if start_time and end_time and start_time >= end_time:
            raise serializers.ValidationError(
                {'start_time': "Event start time must be before end time."}
            )
        return data


# ---------------------------------------------------------------------------
# Voting Poll
# ---------------------------------------------------------------------------

class PollChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PollChoice
        fields = ['id', 'text', 'vote_count']
        read_only_fields = ['id', 'vote_count']


class VotingPollSerializer(serializers.ModelSerializer):
    choices = PollChoiceSerializer(many=True, read_only=True)
    choice_texts = serializers.ListField(
        child=serializers.CharField(max_length=500),
        write_only=True,
        required=True,
        help_text="At least 2 choices required (BR-GYM-012).",
    )

    class Meta:
        model = VotingPoll
        fields = [
            'id', 'club', 'title', 'description', 'expiry_date',
            'target_batches', 'target_branches',
            'created_by', 'created_at',
            'choices', 'choice_texts',
        ]
        read_only_fields = ['id', 'created_by', 'created_at']

    def validate_choice_texts(self, value):
        # BR-GYM-012: at least two choices
        if len(value) < 2:
            raise serializers.ValidationError("A poll must have at least two choices.")
        return value

    def create(self, validated_data):
        choice_texts = validated_data.pop('choice_texts')
        poll = VotingPoll.objects.create(**validated_data)
        for text in choice_texts:
            PollChoice.objects.create(poll=poll, text=text)
        return poll


class PollVoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PollVote
        fields = ['id', 'poll', 'choice', 'voter', 'voted_at']
        read_only_fields = ['id', 'voter', 'voted_at']

    def validate(self, data):
        request = self.context.get('request')
        user = getattr(request, 'user', None) if request else data.get('voter')

        poll = data.get('poll')
        choice = data.get('choice')

        # BR-GYM-014: poll must be active
        if poll and not poll.is_active:
            raise serializers.ValidationError({'poll': "This poll is no longer active."})

        # Choice must belong to the poll
        if poll and choice and choice.poll_id != poll.pk:
            raise serializers.ValidationError({'choice': "Choice does not belong to this poll."})

        # BR-GYM-015: one vote per student per poll
        if poll and user:
            if PollVote.objects.filter(poll=poll, voter=user).exists():
                raise serializers.ValidationError({'poll': "You have already voted in this poll."})

        return data


# ---------------------------------------------------------------------------
# Club Budget Request
# ---------------------------------------------------------------------------

class ClubBudgetRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClubBudgetRequest
        fields = [
            'id', 'club', 'requested_by', 'purpose', 'amount',
            'description', 'supporting_file', 'status', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'requested_by', 'status', 'created_at', 'updated_at']

    def validate_amount(self, value):
        # BR-GYM-017: non-negative
        if value < Decimal('0'):
            raise serializers.ValidationError("Budget amount must be zero or greater.")
        return value

    def validate_supporting_file(self, value):
        # BR-GYM-018: required supporting file
        if not value:
            raise serializers.ValidationError("A supporting file is required for budget requests.")
        return value


# ---------------------------------------------------------------------------
# Club Event Report
# ---------------------------------------------------------------------------

class ClubEventReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClubEventReport
        fields = [
            'id', 'club', 'submitted_by', 'student_incharge',
            'event_name', 'description', 'event_date',
            'report_file', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'submitted_by', 'created_at', 'updated_at']

    def validate_report_file(self, value):
        # BR-GYM-019: required file
        if not value:
            raise serializers.ValidationError("A report file is required for event reports.")
        return value


# ---------------------------------------------------------------------------
# Gymkhana Workflow History
# ---------------------------------------------------------------------------

class GymkhanaWorkflowHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = GymkhanaWorkflowHistory
        fields = [
            'id', 'entity_type', 'entity_id',
            'from_state', 'to_state', 'actor',
            'action_taken', 'remarks', 'timestamp',
        ]
        read_only_fields = [
            'id', 'entity_type', 'entity_id',
            'from_state', 'to_state', 'actor',
            'action_taken', 'timestamp',
        ]


# ---------------------------------------------------------------------------
# Club Membership Action serializer (approve action)
# ---------------------------------------------------------------------------

class MembershipActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['approve'])
    remarks = serializers.CharField(required=False, allow_blank=True, max_length=500)
