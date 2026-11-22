"""Quiz API views: authenticate, scope, delegate and serialize."""

from __future__ import annotations

from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.quiz.api import serializers as s
from modules.quiz.api.exceptions import AcademicAuthorizationUnavailable
from modules.quiz.api.permissions import IsNotStudentPrincipal, IsStudentPrincipal
from modules.quiz.domain.quiz_definition import DefinitionAction
from modules.quiz.models import Question, Quiz, QuizResult
from modules.quiz.selectors import (
    attempt_for_student,
    eligible_quizzes_for_student,
    question_bank_for_creator,
    quiz_for_courses,
    quizzes_for_courses,
    released_results_for_student,
    student_attempt_presentation_rows,
    student_result_rows,
)
from modules.quiz.services import attempts as attempt_service
from modules.quiz.services import authoring as authoring_service
from modules.quiz.services import lifecycle as lifecycle_service
from modules.quiz.services import responses as response_service

MODULE = HasModuleGrant("quiz")


def _actor(request):
    return getattr(request, "principal", None)


def _is_schema_generation(view) -> bool:
    """Detect drf-spectacular's synthetic view, never a caller-controlled flag."""

    return getattr(view, "swagger_fake_view", False)


def _trusted_course_ids(_principal) -> tuple[int, ...]:
    """No production course authorization provider is currently configured."""

    raise AcademicAuthorizationUnavailable()


def _trusted_eligible_quiz_ids(_principal):
    """No production academic enrollment/eligibility provider is configured."""

    raise AcademicAuthorizationUnavailable()


@extend_schema_view(
    get=extend_schema(responses=s.QuizDetailSerializer(many=True)),
    post=extend_schema(
        request=s.QuizDraftCreateSerializer,
        responses={status.HTTP_201_CREATED: s.QuizDetailSerializer},
    ),
)
class QuizListCreateView(generics.ListAPIView):
    permission_classes = [MODULE, IsNotStudentPrincipal]
    serializer_class = s.QuizDetailSerializer

    def get_queryset(self):
        if _is_schema_generation(self):
            return Quiz.objects.none()
        self._require(self.request, "quiz.quiz.view")
        return quizzes_for_courses(_trusted_course_ids(_actor(self.request)))

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        self._require(request, "quiz.quiz.create")
        payload = s.QuizDraftCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = dict(payload.validated_data)
        quiz = authoring_service.create_draft(
            actor=_actor(request),
            authorized_course_ids=_trusted_course_ids(_actor(request)),
            definition=payload.definition(data),
            description=data["description"],
            instructions=data["instructions"],
        )
        return Response(s.QuizDetailSerializer(quiz).data, status=status.HTTP_201_CREATED)

    @staticmethod
    def _require(request, code: str) -> None:
        if not _actor(request).has_permission(code):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied()


@extend_schema_view(
    get=extend_schema(responses=s.QuizDetailSerializer),
    put=extend_schema(
        request=s.QuizDraftUpdateSerializer,
        responses=s.QuizDetailSerializer,
    ),
)
class QuizDetailUpdateView(APIView):
    permission_classes = [MODULE, IsNotStudentPrincipal]

    def get(self, request, public_id):
        self._require(request, "quiz.quiz.view")
        quiz = self._scoped_quiz(request, public_id)
        return Response(s.QuizDetailSerializer(quiz).data)

    def put(self, request, public_id):
        self._require(request, "quiz.quiz.update")
        payload = s.QuizDraftUpdateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = dict(payload.validated_data)
        quiz = authoring_service.update_draft(
            public_id=public_id,
            actor=_actor(request),
            authorized_course_ids=_trusted_course_ids(_actor(request)),
            definition=payload.definition(data),
            description=data.get("description"),
            instructions=data.get("instructions"),
        )
        return Response(s.QuizDetailSerializer(quiz).data)

    @staticmethod
    def _require(request, code: str) -> None:
        if not _actor(request).has_permission(code):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied()

    @staticmethod
    def _scoped_quiz(request, public_id):
        quiz = quiz_for_courses(
            public_id=public_id,
            course_ids=_trusted_course_ids(_actor(request)),
        ).first()
        if quiz is None:
            raise NotFound()
        return quiz


class QuizPublishView(APIView):
    permission_classes = [MODULE, IsNotStudentPrincipal, HasPermission("quiz.quiz.publish")]

    @extend_schema(
        request=s.QuizPublishSerializer,
        responses=s.QuizDetailSerializer,
    )
    def post(self, request, public_id):
        payload = s.QuizPublishSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        action = DefinitionAction(payload.validated_data["action"])
        quiz = lifecycle_service.publish_quiz(
            public_id=public_id,
            actor=_actor(request),
            authorized_course_ids=_trusted_course_ids(_actor(request)),
            action=action,
        )
        return Response(s.QuizDetailSerializer(quiz).data)


@extend_schema_view(get=extend_schema(parameters=[s.QuestionBankSearchSerializer]))
class QuestionBankListView(generics.ListAPIView):
    permission_classes = [MODULE, IsNotStudentPrincipal, HasPermission("quiz.question.view")]
    serializer_class = s.QuestionBankOwnerSerializer

    def get_queryset(self):
        if _is_schema_generation(self):
            return Question.objects.none()
        query = s.QuestionBankSearchSerializer(data=self.request.query_params)
        query.is_valid(raise_exception=True)
        return question_bank_for_creator(
            creator_user_id=_actor(self.request).user_id,
            **query.validated_data,
        )


class QuestionBankDetailView(generics.RetrieveAPIView):
    permission_classes = [MODULE, IsNotStudentPrincipal, HasPermission("quiz.question.view")]
    serializer_class = s.QuestionBankOwnerSerializer
    lookup_field = "public_id"

    def get_queryset(self):
        if _is_schema_generation(self):
            return Question.objects.none()
        return question_bank_for_creator(creator_user_id=_actor(self.request).user_id)


class EligibleQuizListView(generics.ListAPIView):
    permission_classes = [MODULE, HasPermission("quiz.quiz.view"), IsStudentPrincipal]
    serializer_class = s.EligibleQuizSerializer

    def get_queryset(self):
        if _is_schema_generation(self):
            return Quiz.objects.none()
        actor = _actor(self.request)
        return eligible_quizzes_for_student(
            eligible_quiz_ids=_trusted_eligible_quiz_ids(actor),
            student_user_id=actor.user_id,
            server_now=timezone.now(),
        )


class EligibleQuizDetailView(APIView):
    permission_classes = [MODULE, HasPermission("quiz.quiz.view"), IsStudentPrincipal]

    @extend_schema(responses=s.EligibleQuizSerializer)
    def get(self, request, public_id):
        actor = _actor(request)
        quiz = (
            eligible_quizzes_for_student(
                eligible_quiz_ids=_trusted_eligible_quiz_ids(actor),
                student_user_id=actor.user_id,
                server_now=timezone.now(),
            )
            .filter(public_id=public_id)
            .first()
        )
        if quiz is None:
            raise NotFoundError("No eligible Quiz exists.")
        return Response(s.EligibleQuizSerializer(quiz).data)


class StudentAttemptDetailView(APIView):
    permission_classes = [MODULE, HasPermission("quiz.attempt.view"), IsStudentPrincipal]

    @extend_schema(responses=s.StudentAttemptSerializer)
    def get(self, request, attempt_id: int):
        actor = _actor(request)
        attempt = attempt_for_student(
            attempt_id=attempt_id,
            student_user_id=actor.user_id,
        ).first()
        if attempt is None:
            raise NotFoundError("No such Student attempt.")
        rows = list(
            student_attempt_presentation_rows(
                attempt_id=attempt.pk,
                student_user_id=actor.user_id,
            )
        )
        payload = s.StudentAttemptSerializer(
            attempt,
            context={"presentation_rows": rows},
        )
        return Response(payload.data)


class StudentResponseView(APIView):
    permission_classes = [MODULE, HasPermission("quiz.response.update"), IsStudentPrincipal]

    @extend_schema(
        request=s.SaveResponseSerializer,
        responses=s.ResponseSavedSerializer,
    )
    def put(self, request, attempt_id: int, attempt_question_id: int):
        payload = s.SaveResponseSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        saved = response_service.save_response(
            attempt_id=attempt_id,
            attempt_question_id=attempt_question_id,
            actor=_actor(request),
            **payload.validated_data,
        )
        return Response(s.ResponseSavedSerializer(saved).data)


class StudentAttemptSubmitView(APIView):
    permission_classes = [MODULE, HasPermission("quiz.attempt.update"), IsStudentPrincipal]

    @extend_schema(
        request=s.SubmitAttemptSerializer,
        responses=s.AttemptSubmissionResponseSerializer,
    )
    def post(self, request, attempt_id: int):
        payload = s.SubmitAttemptSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        attempt = attempt_service.submit_attempt(attempt_id=attempt_id, actor=_actor(request))
        return Response(
            {
                "attempt_id": attempt.pk,
                "status": attempt.status,
                "submitted_at": attempt.submitted_at,
            }
        )


class StudentReleasedResultListView(generics.ListAPIView):
    permission_classes = [MODULE, HasPermission("quiz.result.view"), IsStudentPrincipal]
    serializer_class = s.ReleasedResultSerializer

    def get_queryset(self):
        if _is_schema_generation(self):
            return QuizResult.objects.none()
        return released_results_for_student(_actor(self.request).user_id)


class StudentReleasedResultDetailView(APIView):
    permission_classes = [MODULE, HasPermission("quiz.result.view"), IsStudentPrincipal]

    @extend_schema(responses=s.ReleasedResultSerializer)
    def get(self, request, result_id: int):
        rows = list(
            student_result_rows(
                student_user_id=_actor(request).user_id,
                result_id=result_id,
            )[:1]
        )
        if not rows:
            raise NotFoundError("No released result exists.")
        return Response(s.ReleasedResultSerializer(rows[0]).data)
