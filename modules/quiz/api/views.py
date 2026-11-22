from decimal import Decimal

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.api.exceptions import BadRequestError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.quiz.api.serializers import (
    AttemptResponseSerializer,
    QuestionBankItemSerializer,
    QuizAttemptSerializer,
    QuizDetailSerializer,
    QuizListSerializer,
    ResponseEvaluationSerializer,
)
from modules.quiz.models import QuizAttempt
from modules.quiz.selectors.evaluations import (
    get_quiz_submissions_overview,
)
from modules.quiz.selectors.questions import search_question_bank
from modules.quiz.selectors.quizzes import get_quiz_by_id, list_quizzes
from modules.quiz.services.attempt_service import (
    record_tab_violation,
    save_response,
    start_quiz_attempt,
    submit_quiz_attempt,
)
from modules.quiz.services.evaluation_service import grade_subjective_response, release_quiz_results
from modules.quiz.services.quiz_service import archive_quiz, create_quiz, publish_quiz, update_quiz


def _get_principal(request):
    p = getattr(request, "principal", None)
    if not p:
        user_id = request.user.id if request.user.is_authenticated else 1
        role = "faculty" if request.user.is_staff else "student"
        return type(
            "StubPrincipal", (), {"user_id": user_id, "active_role": role, "roles": [role]}
        )()
    return p


class QuizViewSet(viewsets.ViewSet):
    def get_permissions(self):
        if self.action in [
            "create",
            "update",
            "partial_update",
            "destroy",
            "publish",
            "archive",
            "submissions",
            "release_results",
            "reports",
        ]:
            return [HasModuleGrant("quiz")(), HasPermission("quiz.manage")()]
        if self.action in ["start"]:
            return [HasModuleGrant("quiz")(), HasPermission("quiz.attempt")()]
        return [
            HasModuleGrant("quiz")(),
            HasPermission("quiz.manage", "quiz.attempt", require_all=False)(),
        ]

    def list(self, request):
        p = _get_principal(request)
        course_id_str = request.query_params.get("course_id")
        course_id = None
        if course_id_str:
            try:
                course_id = int(course_id_str)
            except ValueError:
                raise BadRequestError(
                    "Invalid course_id parameter.", code="INVALID_QUERY_PARAM"
                ) from None

        quizzes = list_quizzes(p.user_id, p.active_role, course_id=course_id)
        serializer = QuizListSerializer(quizzes, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        p = _get_principal(request)
        try:
            quiz_id = int(pk)
        except ValueError:
            raise BadRequestError("Invalid quiz ID.", code="INVALID_ID") from None
        quiz = get_quiz_by_id(quiz_id, p.user_id, p.active_role)
        serializer = QuizDetailSerializer(quiz)
        return Response(serializer.data)

    def create(self, request):
        p = _get_principal(request)
        data = request.data
        try:
            course_id = int(data.get("course_id", 1))
            duration = int(data.get("duration_minutes", 30))
            max_attempts = int(data.get("max_attempts", 1))
        except (ValueError, TypeError):
            raise BadRequestError(
                "Invalid numeric field in quiz creation.", code="INVALID_INPUT"
            ) from None

        quiz = create_quiz(
            course_id=course_id,
            title=data.get("title", ""),
            instructions=data.get("instructions", ""),
            duration_minutes=duration,
            max_attempts=max_attempts,
            created_by_user_id=p.user_id,
        )
        return Response(QuizDetailSerializer(quiz).data, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None):
        p = _get_principal(request)
        quiz = update_quiz(int(pk), p.user_id, **request.data)
        return Response(QuizDetailSerializer(quiz).data)

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        p = _get_principal(request)
        quiz = publish_quiz(int(pk), p.user_id)
        return Response(QuizDetailSerializer(quiz).data)

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        p = _get_principal(request)
        quiz = archive_quiz(int(pk), p.user_id)
        return Response(QuizDetailSerializer(quiz).data)

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        p = _get_principal(request)
        attempt = start_quiz_attempt(int(pk), p.user_id)
        return Response(QuizAttemptSerializer(attempt).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def submissions(self, request, pk=None):
        p = _get_principal(request)
        quiz = get_quiz_by_id(int(pk), p.user_id, p.active_role)
        attempts = QuizAttempt.objects.filter(quiz=quiz).order_by("-created_at")
        return Response(QuizAttemptSerializer(attempts, many=True).data)

    @action(detail=True, methods=["post"], url_path="release-results")
    def release_results(self, request, pk=None):
        p = _get_principal(request)
        count = release_quiz_results(int(pk), p.user_id)
        return Response({"status": "RELEASED", "updated_results_count": count})

    @action(detail=True, methods=["get"])
    def reports(self, request, pk=None):
        p = _get_principal(request)
        # Ensure course scoping
        get_quiz_by_id(int(pk), p.user_id, p.active_role)
        overview = get_quiz_submissions_overview(int(pk))
        return Response(overview)


class QuestionBankViewSet(viewsets.ModelViewSet):
    serializer_class = QuestionBankItemSerializer
    permission_classes = [HasModuleGrant("quiz"), HasPermission("quiz.question_bank.manage")]

    def get_queryset(self):
        p = _get_principal(self.request)
        topic = self.request.query_params.get("topic")
        difficulty = self.request.query_params.get("difficulty")
        qtype = self.request.query_params.get("question_type")
        return search_question_bank(p.user_id, topic, difficulty, qtype)

    def perform_create(self, serializer):
        p = _get_principal(self.request)
        serializer.save(owner_user_id=p.user_id)


class AttemptViewSet(viewsets.ViewSet):
    permission_classes = [HasModuleGrant("quiz"), HasPermission("quiz.attempt")]

    def retrieve(self, request, pk=None):
        p = _get_principal(request)
        from modules.quiz.selectors.scoping import get_scoped_attempt

        attempt = get_scoped_attempt(int(pk), p.user_id, p.active_role)
        return Response(QuizAttemptSerializer(attempt).data)

    @action(detail=True, methods=["post"])
    def save(self, request, pk=None):
        p = _get_principal(request)
        data = request.data
        resp = save_response(
            attempt_id=int(pk),
            student_id=p.user_id,
            question_id=int(data["question_id"]),
            answer=data.get("answer"),
        )
        return Response(AttemptResponseSerializer(resp).data)

    @action(detail=True, methods=["post"])
    def violation(self, request, pk=None):
        p = _get_principal(request)
        res = record_tab_violation(int(pk), p.user_id)
        return Response(res)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        p = _get_principal(request)
        attempt = submit_quiz_attempt(int(pk), p.user_id)
        return Response(QuizAttemptSerializer(attempt).data)


class EvaluationViewSet(viewsets.ViewSet):
    permission_classes = [HasModuleGrant("quiz"), HasPermission("quiz.evaluate")]

    @action(detail=True, methods=["post"])
    def grade(self, request, pk=None):
        p = _get_principal(request)
        marks = Decimal(str(request.data["marks"]))
        feedback = request.data.get("feedback", "")
        ev = grade_subjective_response(int(pk), p.user_id, marks, feedback)
        return Response(ResponseEvaluationSerializer(ev).data)
