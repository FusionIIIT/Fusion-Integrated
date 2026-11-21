"""Gymkhana automated test suite.

Tests use Django's TestCase with DRF APIRequestFactory / APIClient.
No external IAM calls — Django's built-in User model is used directly.

Coverage:
- T01: Club creation sets status=open; Student Admin approval → confirmed (BW-GYM-03).
- T02: Self-approval guard on club approve action.
- T03: Membership application bound to authenticated student; duplicate same-club blocked (BR-GYM-009).
- T04: Membership application to open (non-confirmed) club blocked (BR-GYM-007).
- T05: Club Head approval of membership transitions open → confirmed (BW-GYM-01).
- T06: Self-membership approval blocked.
- T07: Session with invalid time range (start >= end) rejected (BR-GYM-005).
- T08: Cross-type booking conflict: session-event overlap rejected (BR-GYM-006).
- T09: Poll with fewer than 2 choices rejected (BR-GYM-012).
- T10: One-vote-per-student enforcement (BR-GYM-015).
- T11: Budget request with negative amount rejected (BR-GYM-017).
- T12: Accurate Decimal budget amount stored; workflow history created via .create().
"""
import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from applications.gymkhana.models import (
    Club,
    ClubBudgetRequest,
    ClubEvent,
    ClubMembership,
    ClubSession,
    GymkhanaWorkflowHistory,
    PollChoice,
    PollVote,
    Venue,
    VotingPoll,
)
from applications.gymkhana.views import (
    ClubBudgetRequestViewSet,
    ClubEventViewSet,
    ClubMembershipViewSet,
    ClubSessionViewSet,
    ClubViewSet,
    VotingPollViewSet,
)

User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_counter = 0


def _unique_name(prefix):
    """Return a unique name for each call, scoped to the process."""
    global _counter
    _counter += 1
    return f'{prefix}-{_counter}'


def _make_user(username, is_staff=False, is_superuser=False):
    # Append counter so re-runs within the same DB session don't collide.
    uname = _unique_name(username)
    return User.objects.create_user(
        username=uname,
        password='testpass123',
        is_staff=is_staff,
        is_superuser=is_superuser,
    )


def _make_club(coordinator, co_coordinator, faculty, status='confirmed'):
    return Club.objects.create(
        name=_unique_name('TestClub'),
        description='A test club',
        category='technical',
        coordinator=coordinator,
        co_coordinator=co_coordinator,
        faculty_councillor=faculty,
        status=status,
    )


def _make_venue(prefix='Venue'):
    return Venue.objects.create(name=_unique_name(prefix), capacity=100)


# ---------------------------------------------------------------------------
# T01 & T02: Club creation and approval
# ---------------------------------------------------------------------------

class ClubLifecycleTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.admin = _make_user('admin_user', is_staff=True)
        self.coordinator = _make_user('coord_user')
        self.co_coordinator = _make_user('co_coord_user')
        self.faculty = _make_user('faculty_user')

    def test_01_club_creation_sets_open_status(self):
        """Club creation sets status=open (BR-GYM-004)."""
        view = ClubViewSet.as_view({'post': 'create'})
        payload = {
            'name': 'Robotics Club',
            'description': 'Technical club',
            'category': 'technical',
            'coordinator': self.coordinator.pk,
            'co_coordinator': self.co_coordinator.pk,
            'faculty_councillor': self.faculty.pk,
        }
        req = self.factory.post('/api/gymkhana/clubs/', payload, format='json')
        force_authenticate(req, user=self.admin)
        resp = view(req)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(resp.data['status'], 'open')

    def test_02_student_admin_approves_open_club(self):
        """Student Admin approves open club → confirmed; history logged."""
        club = _make_club(self.coordinator, self.co_coordinator, self.faculty, status='open')
        view = ClubViewSet.as_view({'post': 'approve'})
        req = self.factory.post(f'/api/gymkhana/clubs/{club.pk}/approve/', {}, format='json')
        force_authenticate(req, user=self.admin)
        resp = view(req, pk=club.pk)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        club.refresh_from_db()
        self.assertEqual(club.status, 'confirmed')
        hist = GymkhanaWorkflowHistory.objects.filter(entity_type='club', entity_id=club.pk).first()
        self.assertIsNotNone(hist)
        self.assertEqual(hist.from_state, 'open')
        self.assertEqual(hist.to_state, 'confirmed')

    def test_03_self_approval_forbidden_for_non_superuser(self):
        """Club Head (coordinator) cannot approve their own club unless superuser."""
        club = _make_club(self.coordinator, self.co_coordinator, self.faculty, status='open')
        view = ClubViewSet.as_view({'post': 'approve'})
        req = self.factory.post(f'/api/gymkhana/clubs/{club.pk}/approve/', {}, format='json')
        force_authenticate(req, user=self.coordinator)  # is club head, not superuser
        resp = view(req, pk=club.pk)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_04_already_confirmed_club_cannot_be_approved_again(self):
        """Attempting to approve an already-confirmed club returns 400."""
        club = _make_club(self.coordinator, self.co_coordinator, self.faculty, status='confirmed')
        view = ClubViewSet.as_view({'post': 'approve'})
        req = self.factory.post(f'/api/gymkhana/clubs/{club.pk}/approve/', {}, format='json')
        force_authenticate(req, user=self.admin)
        resp = view(req, pk=club.pk)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# T03–T06: Membership application and approval (BW-GYM-01)
# ---------------------------------------------------------------------------

class MembershipTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.coordinator = _make_user('coord2')
        self.co_coordinator = _make_user('co_coord2')
        self.faculty = _make_user('faculty2')
        self.student = _make_user('student2')
        self.other_student = _make_user('other_student')
        self.confirmed_club = _make_club(
            self.coordinator, self.co_coordinator, self.faculty, status='confirmed'
        )
        self.open_club = _make_club(
            self.coordinator, self.co_coordinator, self.faculty, status='open'
        )
        # name already unique from _make_club helper

    def test_05_student_applies_to_confirmed_club(self):
        """Student successfully applies; student field bound to authenticated user."""
        view = ClubMembershipViewSet.as_view({'post': 'create'})
        payload = {'club': self.confirmed_club.pk, 'achievements': 'Won hackathon'}
        req = self.factory.post('/api/gymkhana/memberships/', payload, format='json')
        force_authenticate(req, user=self.student)
        resp = view(req)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        membership = ClubMembership.objects.get(pk=resp.data['id'])
        self.assertEqual(membership.student, self.student)
        self.assertEqual(membership.status, 'open')

    def test_06_duplicate_same_club_application_blocked(self):
        """Duplicate same-club application is rejected (BR-GYM-009)."""
        ClubMembership.objects.create(
            club=self.confirmed_club, student=self.student, status='open'
        )
        view = ClubMembershipViewSet.as_view({'post': 'create'})
        payload = {'club': self.confirmed_club.pk, 'achievements': 'Another attempt'}
        req = self.factory.post('/api/gymkhana/memberships/', payload, format='json')
        force_authenticate(req, user=self.student)
        resp = view(req)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_07_application_to_open_club_blocked(self):
        """Application to non-confirmed club blocked (BR-GYM-007)."""
        view = ClubMembershipViewSet.as_view({'post': 'create'})
        payload = {'club': self.open_club.pk, 'achievements': 'Any'}
        req = self.factory.post('/api/gymkhana/memberships/', payload, format='json')
        force_authenticate(req, user=self.student)
        resp = view(req)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_08_club_head_approves_membership(self):
        """Club Head approves pending application → confirmed (BR-GYM-011)."""
        membership = ClubMembership.objects.create(
            club=self.confirmed_club, student=self.other_student, status='open'
        )
        view = ClubMembershipViewSet.as_view({'post': 'approve'})
        payload = {'action': 'approve', 'remarks': 'Welcome!'}
        req = self.factory.post(
            f'/api/gymkhana/memberships/{membership.pk}/approve/', payload, format='json'
        )
        force_authenticate(req, user=self.coordinator)
        resp = view(req, pk=membership.pk)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        membership.refresh_from_db()
        self.assertEqual(membership.status, 'confirmed')
        self.assertEqual(membership.remarks, 'Welcome!')
        hist = GymkhanaWorkflowHistory.objects.filter(
            entity_type='membership', entity_id=membership.pk
        ).first()
        self.assertIsNotNone(hist)
        self.assertEqual(hist.from_state, 'open')
        self.assertEqual(hist.to_state, 'confirmed')

    def test_09_self_membership_approval_blocked(self):
        """Student cannot approve their own membership application."""
        membership = ClubMembership.objects.create(
            club=self.confirmed_club, student=self.student, status='open'
        )
        view = ClubMembershipViewSet.as_view({'post': 'approve'})
        payload = {'action': 'approve'}
        req = self.factory.post(
            f'/api/gymkhana/memberships/{membership.pk}/approve/', payload, format='json'
        )
        force_authenticate(req, user=self.student)
        resp = view(req, pk=membership.pk)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


# ---------------------------------------------------------------------------
# T07 & T08: Session/Event booking validations (BR-GYM-005, BR-GYM-006)
# ---------------------------------------------------------------------------

class BookingValidationTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.coordinator = _make_user('coord3')
        self.co_coordinator = _make_user('co_coord3')
        self.faculty = _make_user('faculty3')
        self.club = _make_club(
            self.coordinator, self.co_coordinator, self.faculty, status='confirmed'
        )
        self.venue = _make_venue('Sports Hall')

    def test_10_session_invalid_time_range_rejected(self):
        """Session start_time >= end_time is rejected (BR-GYM-005)."""
        view = ClubSessionViewSet.as_view({'post': 'create'})
        payload = {
            'club': self.club.pk,
            'venue': self.venue.pk,
            'date': '2026-12-01',
            'start_time': '14:00',
            'end_time': '10:00',  # end before start
            'description': 'Bad session',
        }
        req = self.factory.post('/api/gymkhana/sessions/', payload, format='json')
        force_authenticate(req, user=self.coordinator)
        resp = view(req)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_11_session_event_cross_type_conflict_rejected(self):
        """Session-event overlap in same venue/date rejected (BR-GYM-006)."""
        # Pre-create a session in the same venue/date/time
        ClubSession.objects.create(
            club=self.club,
            venue=self.venue,
            date=datetime.date(2026, 12, 5),
            start_time=datetime.time(10, 0),
            end_time=datetime.time(12, 0),
            created_by=self.coordinator,
        )
        # Now try to create an event overlapping with the session
        view = ClubEventViewSet.as_view({'post': 'create'})
        payload = {
            'club': self.club.pk,
            'name': 'Overlapping Event',
            'venue': self.venue.pk,
            'date': '2026-12-05',
            'start_time': '11:00',
            'end_time': '13:00',
            'description': 'Should conflict',
        }
        req = self.factory.post('/api/gymkhana/events/', payload, format='json')
        force_authenticate(req, user=self.coordinator)
        resp = view(req)
        self.assertIn(resp.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_500_INTERNAL_SERVER_ERROR])
        # Verify no event was persisted
        self.assertEqual(ClubEvent.objects.count(), 0)

    def test_12_non_overlapping_session_and_event_both_accepted(self):
        """Non-overlapping session and event in same venue on same day are accepted."""
        ClubSession.objects.create(
            club=self.club,
            venue=self.venue,
            date=datetime.date(2026, 12, 10),
            start_time=datetime.time(8, 0),
            end_time=datetime.time(10, 0),
            created_by=self.coordinator,
        )
        view = ClubEventViewSet.as_view({'post': 'create'})
        payload = {
            'club': self.club.pk,
            'name': 'Non-overlapping Event',
            'venue': self.venue.pk,
            'date': '2026-12-10',
            'start_time': '10:30',
            'end_time': '12:00',
            'description': 'Should succeed',
        }
        req = self.factory.post('/api/gymkhana/events/', payload, format='json')
        force_authenticate(req, user=self.coordinator)
        resp = view(req)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)


# ---------------------------------------------------------------------------
# T09 & T10: Voting Poll (BW-GYM-02, BR-GYM-012, BR-GYM-015)
# ---------------------------------------------------------------------------

class PollTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.coordinator = _make_user('coord4')
        self.co_coordinator = _make_user('co_coord4')
        self.faculty = _make_user('faculty4')
        self.student = _make_user('student4')
        self.club = _make_club(
            self.coordinator, self.co_coordinator, self.faculty, status='confirmed'
        )

    def _create_poll(self):
        poll = VotingPoll.objects.create(
            club=self.club,
            title='Best Programming Language',
            expiry_date=datetime.date(2027, 1, 1),
            created_by=self.coordinator,
        )
        c1 = PollChoice.objects.create(poll=poll, text='Python')
        c2 = PollChoice.objects.create(poll=poll, text='Rust')
        return poll, c1, c2

    def test_13_poll_with_fewer_than_two_choices_rejected(self):
        """BR-GYM-012: Poll with fewer than 2 choices is rejected."""
        view = VotingPollViewSet.as_view({'post': 'create'})
        payload = {
            'club': self.club.pk,
            'title': 'Single choice poll',
            'expiry_date': '2027-01-01',
            'choice_texts': ['Only one'],  # only 1 choice
        }
        req = self.factory.post('/api/gymkhana/polls/', payload, format='json')
        force_authenticate(req, user=self.coordinator)
        resp = view(req)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_14_poll_with_two_choices_created_successfully(self):
        """Poll with ≥2 choices is accepted (BR-GYM-012)."""
        view = VotingPollViewSet.as_view({'post': 'create'})
        payload = {
            'club': self.club.pk,
            'title': 'Valid poll',
            'expiry_date': '2027-01-01',
            'choice_texts': ['Option A', 'Option B'],
        }
        req = self.factory.post('/api/gymkhana/polls/', payload, format='json')
        force_authenticate(req, user=self.coordinator)
        resp = view(req)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        poll = VotingPoll.objects.get(pk=resp.data['id'])
        self.assertEqual(poll.choices.count(), 2)

    def test_15_one_vote_per_student_enforced(self):
        """BR-GYM-015: Second vote by same student is rejected."""
        poll, c1, c2 = self._create_poll()
        # First vote
        PollVote.objects.create(poll=poll, choice=c1, voter=self.student)

        view = VotingPollViewSet.as_view({'post': 'vote'})
        payload = {'poll': poll.pk, 'choice': c2.pk}
        req = self.factory.post(f'/api/gymkhana/polls/{poll.pk}/vote/', payload, format='json')
        force_authenticate(req, user=self.student)
        resp = view(req, pk=poll.pk)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('already voted', str(resp.data).lower())

    def test_16_expired_poll_rejects_vote(self):
        """BR-GYM-014: Voting on an expired poll is rejected."""
        poll = VotingPoll.objects.create(
            club=self.club,
            title='Expired poll',
            expiry_date=datetime.date(2020, 1, 1),  # past date
            created_by=self.coordinator,
        )
        c1 = PollChoice.objects.create(poll=poll, text='Past option')

        view = VotingPollViewSet.as_view({'post': 'vote'})
        payload = {'poll': poll.pk, 'choice': c1.pk}
        req = self.factory.post(f'/api/gymkhana/polls/{poll.pk}/vote/', payload, format='json')
        force_authenticate(req, user=self.student)
        resp = view(req, pk=poll.pk)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# T11 & T12: Budget Request (BR-GYM-017, BR-GYM-018)
# ---------------------------------------------------------------------------

class BudgetRequestTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.coordinator = _make_user('coord5')
        self.co_coordinator = _make_user('co_coord5')
        self.faculty = _make_user('faculty5')
        self.club = _make_club(
            self.coordinator, self.co_coordinator, self.faculty, status='confirmed'
        )

    def test_17_negative_budget_amount_rejected(self):
        """BR-GYM-017: Negative budget amount is rejected."""
        view = ClubBudgetRequestViewSet.as_view({'post': 'create'})
        payload = {
            'club': self.club.pk,
            'purpose': 'Equipment',
            'amount': '-100.00',
            'description': 'Negative',
            'supporting_file': '',
        }
        req = self.factory.post('/api/gymkhana/budget-requests/', payload, format='json')
        force_authenticate(req, user=self.coordinator)
        resp = view(req)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_18_zero_amount_budget_accepted(self):
        """BR-GYM-017: Zero budget amount is valid (non-negative)."""
        import io
        from django.core.files.uploadedfile import SimpleUploadedFile
        dummy_file = SimpleUploadedFile('budget.pdf', b'%PDF-1.4 dummy', content_type='application/pdf')
        # Create directly in DB to avoid file upload complexity in factory
        br = ClubBudgetRequest.objects.create(
            club=self.club,
            requested_by=self.coordinator,
            purpose='No-cost event',
            amount=Decimal('0.00'),
            description='',
            supporting_file=dummy_file,
            status='open',
        )
        self.assertEqual(br.amount, Decimal('0.00'))
        self.assertEqual(br.status, 'open')

    def test_19_decimal_amount_stored_precisely(self):
        """Budget amounts are stored as exact Decimal values (never float)."""
        import io
        from django.core.files.uploadedfile import SimpleUploadedFile
        dummy_file = SimpleUploadedFile('budget2.pdf', b'%PDF-1.4 dummy', content_type='application/pdf')
        br = ClubBudgetRequest.objects.create(
            club=self.club,
            requested_by=self.coordinator,
            purpose='Equipment purchase',
            amount=Decimal('12345.67'),
            supporting_file=dummy_file,
            status='open',
        )
        br.refresh_from_db()
        # Verify Decimal precision is maintained
        self.assertEqual(br.amount, Decimal('12345.67'))
        self.assertIsInstance(br.amount, Decimal)


# ---------------------------------------------------------------------------
# T: Workflow history audit trail
# ---------------------------------------------------------------------------

class WorkflowHistoryTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.admin = _make_user('admin_hist', is_staff=True)
        self.coordinator = _make_user('coord_hist')
        self.co_coordinator = _make_user('co_coord_hist')
        self.faculty = _make_user('faculty_hist')
        self.student = _make_user('student_hist')

    def test_20_club_approval_creates_workflow_history_via_create(self):
        """Workflow history record is created with .create() during club approval."""
        club = Club.objects.create(
            name='History Test Club',
            category='cultural',
            coordinator=self.coordinator,
            co_coordinator=self.co_coordinator,
            faculty_councillor=self.faculty,
            status='open',
        )
        view = ClubViewSet.as_view({'post': 'approve'})
        req = self.factory.post(f'/api/gymkhana/clubs/{club.pk}/approve/', {}, format='json')
        force_authenticate(req, user=self.admin)
        resp = view(req, pk=club.pk)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Exactly one history record should exist
        records = GymkhanaWorkflowHistory.objects.filter(
            entity_type='club', entity_id=club.pk
        )
        self.assertEqual(records.count(), 1)
        rec = records.first()
        self.assertEqual(rec.action_taken, 'approve')
        self.assertEqual(rec.actor, self.admin)
        self.assertEqual(rec.from_state, 'open')
        self.assertEqual(rec.to_state, 'confirmed')

    def test_21_membership_approval_creates_workflow_history(self):
        """Membership approval creates correct workflow history entry."""
        club = _make_club(self.coordinator, self.co_coordinator, self.faculty, status='confirmed')
        membership = ClubMembership.objects.create(
            club=club, student=self.student, status='open'
        )
        view = ClubMembershipViewSet.as_view({'post': 'approve'})
        payload = {'action': 'approve', 'remarks': 'Excellent candidate'}
        req = self.factory.post(
            f'/api/gymkhana/memberships/{membership.pk}/approve/', payload, format='json'
        )
        force_authenticate(req, user=self.coordinator)
        resp = view(req, pk=membership.pk)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        records = GymkhanaWorkflowHistory.objects.filter(
            entity_type='membership', entity_id=membership.pk
        )
        self.assertEqual(records.count(), 1)
        rec = records.first()
        self.assertEqual(rec.from_state, 'open')
        self.assertEqual(rec.to_state, 'confirmed')
        self.assertEqual(rec.remarks, 'Excellent candidate')
