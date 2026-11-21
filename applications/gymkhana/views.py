"""Gymkhana views.

ViewSets reference self.request (not self.context).
perform_create binds authenticated user: serializer.save(user=self.request.user, ...).
Self-approval is explicitly forbidden for non-superusers.
Decimal arithmetic uses Decimal(str(val)) to avoid TypeError with floats.
Workflow history records use .create() (never .get_or_create()).
"""
from decimal import Decimal

from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

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
from .serializers import (
    ClubBudgetRequestSerializer,
    ClubEventReportSerializer,
    ClubEventSerializer,
    ClubMembershipSerializer,
    ClubSerializer,
    ClubSessionSerializer,
    GymkhanaWorkflowHistorySerializer,
    MembershipActionSerializer,
    PollVoteSerializer,
    VenueSerializer,
    VotingPollSerializer,
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _log_history(entity_type, entity_id, from_state, to_state, actor, action_taken, remarks=""):
    """Create a single audit-history record (never get_or_create)."""
    GymkhanaWorkflowHistory.objects.create(
        entity_type=entity_type,
        entity_id=entity_id,
        from_state=from_state,
        to_state=to_state,
        actor=actor,
        action_taken=action_taken,
        remarks=remarks,
    )


# ---------------------------------------------------------------------------
# Venue
# ---------------------------------------------------------------------------

class VenueViewSet(viewsets.ModelViewSet):
    """CRUD for configured Gymkhana venues (BR-GYM-020)."""
    queryset = Venue.objects.all()
    serializer_class = VenueSerializer
    permission_classes = [IsAuthenticated]


# ---------------------------------------------------------------------------
# Club (UC-GYM-001, UC-GYM-011)
# ---------------------------------------------------------------------------

class ClubViewSet(viewsets.ModelViewSet):
    """
    Club lifecycle: Student Admin creates (open) and approves (confirmed).

    Custom actions:
    - POST /clubs/{pk}/approve/ — Student Admin confirms an open club (UC-GYM-011, BW-GYM-03).
    """
    queryset = Club.objects.select_related(
        'coordinator', 'co_coordinator', 'faculty_councillor'
    ).all()
    serializer_class = ClubSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        """New clubs start as open (BR-GYM-004)."""
        serializer.save(status='open')

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """UC-GYM-011: Student Admin approves an open club → confirmed."""
        club = self.get_object()

        # Self-approval guard: non-superusers cannot approve if they are club leaders
        if club.is_head(request.user) and not request.user.is_superuser:
            return Response(
                {'detail': 'Self-approval forbidden.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if club.status != 'open':
            return Response(
                {'detail': 'Only open clubs can be approved.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        prior_state = club.status
        club.status = 'confirmed'
        club.save()

        _log_history('club', club.pk, prior_state, 'confirmed', request.user, 'approve')

        serializer = self.get_serializer(club)
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# Club Membership (UC-GYM-004, UC-GYM-005, BW-GYM-01)
# ---------------------------------------------------------------------------

class ClubMembershipViewSet(viewsets.ModelViewSet):
    """
    Membership application intake and approval.

    Custom actions:
    - POST /memberships/{pk}/approve/ — Club Head approves a pending application (UC-GYM-005).
    """
    serializer_class = ClubMembershipSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return ClubMembership.objects.select_related('club', 'student').all()
        # Club heads see applications for their clubs; students see their own
        return ClubMembership.objects.select_related('club', 'student').filter(
            club__coordinator=user
        ) | ClubMembership.objects.filter(
            club__co_coordinator=user
        ) | ClubMembership.objects.filter(student=user)

    def perform_create(self, serializer):
        """Bind the authenticated student and set status = 'open'."""
        serializer.save(student=self.request.user, status='open')

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """UC-GYM-005: Club Head approves an open membership application."""
        membership = self.get_object()

        # Self-approval guard
        if membership.student == request.user and not request.user.is_superuser:
            return Response(
                {'detail': 'Self-approval forbidden.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        # BR-GYM-010: Only applicable Club Head may approve
        if not membership.club.is_head(request.user) and not request.user.is_superuser:
            return Response(
                {'detail': 'Only the applicable Club Head may approve membership applications.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if membership.status != 'open':
            return Response(
                {'detail': 'Only open membership applications can be approved.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        action_serializer = MembershipActionSerializer(data=request.data)
        action_serializer.is_valid(raise_exception=True)
        remarks = action_serializer.validated_data.get('remarks', '')

        prior_state = membership.status
        membership.status = 'confirmed'
        membership.remarks = remarks
        membership.save()

        _log_history('membership', membership.pk, prior_state, 'confirmed', request.user, 'approve', remarks)

        serializer = self.get_serializer(membership)
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# Club Session (UC-GYM-002)
# ---------------------------------------------------------------------------

class ClubSessionViewSet(viewsets.ModelViewSet):
    """Session booking with cross-type venue conflict detection (BR-GYM-005, BR-GYM-006)."""
    serializer_class = ClubSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ClubSession.objects.select_related('club', 'venue', 'created_by').all()

    def perform_create(self, serializer):
        """Run full_clean (which calls clean() on model) before saving."""
        instance = serializer.save(created_by=self.request.user)
        # Trigger model-level cross-type conflict check via full_clean
        try:
            instance.full_clean()
        except Exception as exc:
            instance.delete()
            from rest_framework.exceptions import ValidationError as DRFValidationError
            raise DRFValidationError(str(exc))

    def perform_update(self, serializer):
        instance = serializer.save()
        try:
            instance.full_clean()
        except Exception as exc:
            from rest_framework.exceptions import ValidationError as DRFValidationError
            raise DRFValidationError(str(exc))


# ---------------------------------------------------------------------------
# Club Event (UC-GYM-003)
# ---------------------------------------------------------------------------

class ClubEventViewSet(viewsets.ModelViewSet):
    """Event booking with cross-type venue conflict detection (BR-GYM-005, BR-GYM-006)."""
    serializer_class = ClubEventSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ClubEvent.objects.select_related('club', 'venue', 'created_by').all()

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        try:
            instance.full_clean()
        except Exception as exc:
            instance.delete()
            from rest_framework.exceptions import ValidationError as DRFValidationError
            raise DRFValidationError(str(exc))

    def perform_update(self, serializer):
        instance = serializer.save()
        try:
            instance.full_clean()
        except Exception as exc:
            from rest_framework.exceptions import ValidationError as DRFValidationError
            raise DRFValidationError(str(exc))


# ---------------------------------------------------------------------------
# Voting Poll (UC-GYM-006, UC-GYM-007, BW-GYM-02)
# ---------------------------------------------------------------------------

class VotingPollViewSet(viewsets.ModelViewSet):
    """Poll creation with minimum-2-choices and targeted audience."""
    serializer_class = VotingPollSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return VotingPoll.objects.prefetch_related('choices').select_related('club', 'created_by').all()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def vote(self, request, pk=None):
        """UC-GYM-007: Student casts one vote in an eligible poll."""
        poll = self.get_object()

        # BR-GYM-014: poll must be active
        if not poll.is_active:
            return Response(
                {'detail': 'This poll has expired.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # BR-GYM-015: one vote per student per poll
        if PollVote.objects.filter(poll=poll, voter=request.user).exists():
            return Response(
                {'detail': 'You have already voted in this poll.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        vote_serializer = PollVoteSerializer(
            data=request.data,
            context={'request': request},
        )
        vote_serializer.is_valid(raise_exception=True)
        choice = vote_serializer.validated_data['choice']

        # Ensure choice belongs to this poll
        if choice.poll_id != poll.pk:
            return Response(
                {'detail': 'Choice does not belong to this poll.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        vote_serializer.save(voter=request.user, poll=poll)

        # Update vote count
        choice.vote_count = PollVote.objects.filter(choice=choice).count()
        choice.save(update_fields=['vote_count'])

        return Response(vote_serializer.data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Club Budget Request (UC-GYM-009)
# ---------------------------------------------------------------------------

class ClubBudgetRequestViewSet(viewsets.ModelViewSet):
    """Budget request submission and tracking (BR-GYM-017, BR-GYM-018)."""
    serializer_class = ClubBudgetRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return ClubBudgetRequest.objects.select_related('club', 'requested_by').all()
        return ClubBudgetRequest.objects.filter(
            club__coordinator=user
        ) | ClubBudgetRequest.objects.filter(club__co_coordinator=user)

    def perform_create(self, serializer):
        serializer.save(requested_by=self.request.user, status='open')


# ---------------------------------------------------------------------------
# Club Event Report (UC-GYM-010, UC-GYM-012)
# ---------------------------------------------------------------------------

class ClubEventReportViewSet(viewsets.ModelViewSet):
    """Event report submission (Club Head) and review (Faculty Councillor)."""
    serializer_class = ClubEventReportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return ClubEventReport.objects.select_related('club', 'submitted_by').all()
        # BR-GYM-021: Faculty Councillor may access reports for their assigned club
        # Club Heads may access reports for their own club
        return ClubEventReport.objects.filter(
            club__faculty_councillor=user
        ) | ClubEventReport.objects.filter(
            club__coordinator=user
        ) | ClubEventReport.objects.filter(club__co_coordinator=user)

    def perform_create(self, serializer):
        serializer.save(submitted_by=self.request.user)


# ---------------------------------------------------------------------------
# Gymkhana Workflow History (read-only audit log)
# ---------------------------------------------------------------------------

class GymkhanaWorkflowHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only audit log of all Gymkhana state transitions."""
    queryset = GymkhanaWorkflowHistory.objects.select_related('actor').all()
    serializer_class = GymkhanaWorkflowHistorySerializer
    permission_classes = [IsAuthenticated]
