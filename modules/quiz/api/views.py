"""Quiz API views."""
from __future__ import annotations

from django.db.models import Avg, Count, Max, Min, Q
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.quiz.api import serializers as s
from modules.quiz.domain.errors import (
    AttemptAlreadySubmitted,
    AttemptLimitExceeded,
    AttemptNotActive,
    EvaluationError,
    InvalidAttemptTransition,
    InvalidQuizTransition,
    QuizDomainError,
    QuizNotAvailable,
    QuizNotEditable,
)
from modules.quiz.models import Question, Quiz, QuizAttempt
from modules.quiz.selectors import attempts as attempt_selectors
from modules.quiz.selectors import quizzes as quiz_selectors
from modules.quiz.services import attempts as attempt_service
from modules.quiz.services import evaluation as eval_service
from modules.quiz.services import questions as question_service
from modules.quiz.services import quizzes as quiz_service

MODULE = HasModuleGrant("quiz")
P_MANAGE = HasPermission("quiz.quiz.manage")
P_PUBLISH = HasPermission("quiz.quiz.publish")
P_VIEW = HasPermission("quiz.quiz.view")
P_START = HasPermission("quiz.attempt.start")
P_VIEW_OWN = HasPermission("quiz.attempt.view_own")
P_EVALUATE = HasPermission("quiz.evaluation.manage")
P_REPORT = HasPermission("quiz.report.view")


def _principal(request):
    return getattr(request, "principal", None)


def _map_domain_error(exc: QuizDomainError) -> None:
    """Map domain errors to DRF HTTP responses."""
    if isinstance(exc, (QuizNotAvailable, AttemptLimitExceeded)):
        raise ConflictError(str(exc)) from exc
    if isinstance(exc, QuizNotEditable):
        raise ConflictError(str(exc)) from exc
    if isinstance(exc, (AttemptAlreadySubmitted, AttemptNotActive)):
        raise ConflictError(str(exc)) from exc
    if isinstance(exc, (InvalidQuizTransition, InvalidAttemptTransition)):
        raise ConflictError(str(exc)) from exc
    if isinstance(exc, EvaluationError):
        raise ConflictError(str(exc)) from exc
    raise BadRequestError(str(exc)) from exc


# ===========================================================================
# Professor — Quiz CRUD
# ===========================================================================

class QuizListCreateView(generics.GenericAPIView):
    permission_classes = [MODULE, P_MANAGE]
    serializer_class = s.QuizListSerializer

    @extend_schema(
        operation_id="quiz_quizzes_list",
        summary="List professor's quizzes",
        tags=["quiz"],
    )
    def get(self, request):
        qs = quiz_selectors.quizzes_for_professor(_principal(request))
        ser = s.QuizListSerializer(qs, many=True)
        return Response({"results": ser.data})

    @extend_schema(
        operation_id="quiz_quizzes_create",
        summary="Create a new quiz",
        tags=["quiz"],
        request=s.QuizWriteSerializer,
        responses=s.QuizDetailSerializer,
    )
    def post(self, request):
        payload = s.QuizWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            quiz = quiz_service.create_quiz(
                principal=_principal(request), **payload.validated_data
            )
        except QuizDomainError as exc:
            _map_domain_error(exc)
        return Response(
            s.QuizDetailSerializer(quiz).data, status=status.HTTP_201_CREATED
        )


class QuizDetailView(generics.GenericAPIView):
    permission_classes = [MODULE, P_MANAGE]
    serializer_class = s.QuizDetailSerializer

    @extend_schema(
        operation_id="quiz_quiz_retrieve",
        summary="Retrieve a quiz",
        tags=["quiz"],
    )
    def get(self, request, pk):
        try:
            quiz = quiz_selectors.quiz_detail_for_professor(pk, _principal(request))
        except Quiz.DoesNotExist as exc:
            raise NotFoundError("Quiz not found.") from exc
        return Response(s.QuizDetailSerializer(quiz).data)

    @extend_schema(
        operation_id="quiz_quiz_update",
        summary="Update a quiz (Draft only)",
        tags=["quiz"],
        request=s.QuizWriteSerializer,
        responses=s.QuizDetailSerializer,
    )
    def patch(self, request, pk):
        payload = s.QuizWriteSerializer(data=request.data, partial=True)
        payload.is_valid(raise_exception=True)
        try:
            quiz = quiz_service.update_quiz(
                quiz_id=pk, principal=_principal(request), **payload.validated_data
            )
        except Quiz.DoesNotExist as exc:
            raise NotFoundError("Quiz not found.") from exc
        except QuizDomainError as exc:
            _map_domain_error(exc)
        return Response(s.QuizDetailSerializer(quiz).data)

    @extend_schema(
        operation_id="quiz_quiz_delete",
        summary="Delete a quiz (Draft only)",
        tags=["quiz"],
    )
    def delete(self, request, pk):
        try:
            quiz_service.delete_quiz(quiz_id=pk, principal=_principal(request))
        except Quiz.DoesNotExist as exc:
            raise NotFoundError("Quiz not found.") from exc
        except QuizDomainError as exc:
            _map_domain_error(exc)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PublishQuizView(APIView):
    permission_classes = [MODULE, P_PUBLISH]

    @extend_schema(
        operation_id="quiz_publish",
        summary="Publish or schedule a quiz",
        tags=["quiz"],
        request=None,
        responses=s.QuizDetailSerializer,
    )
    def post(self, request, pk):
        try:
            quiz = quiz_service.publish_quiz(
                quiz_id=pk, principal=_principal(request)
            )
        except Quiz.DoesNotExist as exc:
            raise NotFoundError("Quiz not found.") from exc
        except QuizDomainError as exc:
            _map_domain_error(exc)
        return Response(s.QuizDetailSerializer(quiz).data)


class CloseQuizView(APIView):
    permission_classes = [MODULE, P_MANAGE]

    @extend_schema(
        operation_id="quiz_close",
        summary="Close an active quiz",
        tags=["quiz"],
        request=None,
        responses=s.QuizDetailSerializer,
    )
    def post(self, request, pk):
        try:
            quiz = quiz_service.close_quiz(
                quiz_id=pk, principal=_principal(request)
            )
        except Quiz.DoesNotExist as exc:
            raise NotFoundError("Quiz not found.") from exc
        except QuizDomainError as exc:
            _map_domain_error(exc)
        return Response(s.QuizDetailSerializer(quiz).data)


class ArchiveQuizView(APIView):
    permission_classes = [MODULE, P_MANAGE]

    @extend_schema(
        operation_id="quiz_archive",
        summary="Archive a closed quiz",
        tags=["quiz"],
        request=None,
        responses=s.QuizDetailSerializer,
    )
    def post(self, request, pk):
        try:
            quiz = quiz_service.archive_quiz(
                quiz_id=pk, principal=_principal(request)
            )
        except Quiz.DoesNotExist as exc:
            raise NotFoundError("Quiz not found.") from exc
        except QuizDomainError as exc:
            _map_domain_error(exc)
        return Response(s.QuizDetailSerializer(quiz).data)


# ===========================================================================
# Professor — Question Management
# ===========================================================================

class QuestionListCreateView(generics.GenericAPIView):
    permission_classes = [MODULE, P_MANAGE]
    serializer_class = s.QuestionSerializer

    @extend_schema(
        operation_id="quiz_questions_list",
        summary="List questions for a quiz",
        tags=["quiz"],
    )
    def get(self, request, quiz_pk):
        try:
            quiz_selectors.quiz_detail_for_professor(quiz_pk, _principal(request))
        except Quiz.DoesNotExist as exc:
            raise NotFoundError("Quiz not found.") from exc
        questions = Question.objects.filter(quiz_id=quiz_pk).order_by("order", "id")
        return Response({"results": s.QuestionSerializer(questions, many=True).data})

    @extend_schema(
        operation_id="quiz_questions_create",
        summary="Add a question to a quiz",
        tags=["quiz"],
        request=s.QuestionWriteSerializer,
        responses=s.QuestionSerializer,
    )
    def post(self, request, quiz_pk):
        payload = s.QuestionWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            question = question_service.add_question(
                quiz_id=quiz_pk, principal=_principal(request),
                **payload.validated_data
            )
        except Quiz.DoesNotExist as exc:
            raise NotFoundError("Quiz not found.") from exc
        except QuizDomainError as exc:
            _map_domain_error(exc)
        return Response(
            s.QuestionSerializer(question).data, status=status.HTTP_201_CREATED
        )


class QuestionDetailView(generics.GenericAPIView):
    permission_classes = [MODULE, P_MANAGE]
    serializer_class = s.QuestionSerializer

    @extend_schema(
        operation_id="quiz_question_update",
        summary="Update a question",
        tags=["quiz"],
        request=s.QuestionWriteSerializer,
        responses=s.QuestionSerializer,
    )
    def patch(self, request, pk):
        payload = s.QuestionWriteSerializer(data=request.data, partial=True)
        payload.is_valid(raise_exception=True)
        try:
            question = question_service.update_question(
                question_id=pk, principal=_principal(request),
                **payload.validated_data
            )
        except Question.DoesNotExist as exc:
            raise NotFoundError("Question not found.") from exc
        except QuizDomainError as exc:
            _map_domain_error(exc)
        return Response(s.QuestionSerializer(question).data)

    @extend_schema(
        operation_id="quiz_question_delete",
        summary="Delete a question",
        tags=["quiz"],
    )
    def delete(self, request, pk):
        try:
            question_service.delete_question(
                question_id=pk, principal=_principal(request)
            )
        except Question.DoesNotExist as exc:
            raise NotFoundError("Question not found.") from exc
        except QuizDomainError as exc:
            _map_domain_error(exc)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ===========================================================================
# Professor — Question Bank
# ===========================================================================

class QuestionBankListView(generics.GenericAPIView):
    permission_classes = [MODULE, P_MANAGE]
    serializer_class = s.QuestionSerializer

    @extend_schema(
        operation_id="quiz_bank_list",
        summary="List question bank (reusable questions)",
        tags=["quiz"],
    )
    def get(self, request):
        principal = _principal(request)
        qs = Question.objects.filter(
            is_bank_question=True,
            quiz__created_by_user_id=principal.erp_user_id,
        ).select_related("quiz").order_by("-id")

        topic = request.query_params.get("topic")
        difficulty = request.query_params.get("difficulty")
        qtype = request.query_params.get("question_type")
        if topic:
            qs = qs.filter(topic__icontains=topic)
        if difficulty:
            qs = qs.filter(difficulty=difficulty)
        if qtype:
            qs = qs.filter(question_type=qtype)

        return Response({"results": s.QuestionSerializer(qs, many=True).data})


class AddBankQuestionToQuizView(APIView):
    permission_classes = [MODULE, P_MANAGE]

    @extend_schema(
        operation_id="quiz_bank_add_to_quiz",
        summary="Add a bank question to a quiz",
        tags=["quiz"],
        request=s.AddBankQuestionSerializer,
        responses=s.QuestionSerializer,
    )
    def post(self, request, pk):
        payload = s.AddBankQuestionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        quiz_id = payload.validated_data["quiz_id"]
        try:
            question = question_service.add_bank_question_to_quiz(
                bank_question_id=pk,
                quiz_id=quiz_id,
                principal=_principal(request),
            )
        except (Question.DoesNotExist, Quiz.DoesNotExist) as exc:
            raise NotFoundError("Question or quiz not found.") from exc
        except QuizDomainError as exc:
            _map_domain_error(exc)
        return Response(
            s.QuestionSerializer(question).data, status=status.HTTP_201_CREATED
        )


# ===========================================================================
# Professor — Submissions / Evaluation
# ===========================================================================

class QuizSubmissionsView(generics.GenericAPIView):
    permission_classes = [MODULE, P_EVALUATE]
    serializer_class = s.QuizAttemptSerializer

    @extend_schema(
        operation_id="quiz_submissions_list",
        summary="List all submissions for a quiz",
        tags=["quiz"],
    )
    def get(self, request, quiz_pk):
        try:
            quiz_selectors.quiz_detail_for_professor(quiz_pk, _principal(request))
        except Quiz.DoesNotExist as exc:
            raise NotFoundError("Quiz not found.") from exc
        qs = attempt_selectors.attempts_for_quiz(quiz_pk, _principal(request))
        return Response({"results": s.QuizAttemptSerializer(qs, many=True).data})


class AttemptEvaluationView(generics.GenericAPIView):
    permission_classes = [MODULE, P_EVALUATE]
    serializer_class = s.AttemptDetailSerializer

    @extend_schema(
        operation_id="quiz_attempt_eval_retrieve",
        summary="Get attempt for evaluation",
        tags=["quiz"],
    )
    def get(self, request, pk):
        principal = _principal(request)
        try:
            attempt = QuizAttempt.objects.select_related("quiz").prefetch_related(
                "responses__question"
            ).get(pk=pk, quiz__created_by_user_id=principal.erp_user_id)
        except QuizAttempt.DoesNotExist as exc:
            raise NotFoundError("Attempt not found.") from exc
        return Response(s.AttemptDetailSerializer(attempt).data)

    @extend_schema(
        operation_id="quiz_attempt_eval_submit",
        summary="Evaluate subjective responses",
        tags=["quiz"],
        request=s.EvaluateAttemptSerializer,
        responses=s.AttemptDetailSerializer,
    )
    def post(self, request, pk):
        payload = s.EvaluateAttemptSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            attempt = eval_service.evaluate_subjective(
                attempt_id=pk,
                principal=_principal(request),
                response_evaluations=payload.validated_data["responses"],
            )
        except QuizAttempt.DoesNotExist as exc:
            raise NotFoundError("Attempt not found.") from exc
        except QuizDomainError as exc:
            _map_domain_error(exc)
        return Response(s.AttemptDetailSerializer(attempt).data)


class ReleaseAttemptResultView(APIView):
    permission_classes = [MODULE, P_EVALUATE]

    @extend_schema(
        operation_id="quiz_attempt_release",
        summary="Release result for a single attempt",
        tags=["quiz"],
        request=None,
        responses=s.QuizAttemptSerializer,
    )
    def post(self, request, pk):
        try:
            attempt = eval_service.release_attempt_result(
                attempt_id=pk, principal=_principal(request)
            )
        except QuizAttempt.DoesNotExist as exc:
            raise NotFoundError("Attempt not found.") from exc
        except QuizDomainError as exc:
            _map_domain_error(exc)
        return Response(s.QuizAttemptSerializer(attempt).data)


class ReleaseAllResultsView(APIView):
    permission_classes = [MODULE, P_EVALUATE]

    @extend_schema(
        operation_id="quiz_release_all",
        summary="Release all evaluated results for a quiz",
        tags=["quiz"],
        request=None,
        responses=s.ReleaseAllResultSerializer,
    )
    def post(self, request, quiz_pk):
        try:
            count = eval_service.release_all_results(
                quiz_id=quiz_pk, principal=_principal(request)
            )
        except Quiz.DoesNotExist as exc:
            raise NotFoundError("Quiz not found.") from exc
        except QuizDomainError as exc:
            _map_domain_error(exc)
        return Response({"released": count})


# ===========================================================================
# Professor — Reports
# ===========================================================================

class QuizReportView(APIView):
    permission_classes = [MODULE, P_REPORT]

    @extend_schema(
        operation_id="quiz_report",
        summary="Quiz performance report",
        tags=["quiz"],
        responses=s.QuizReportSerializer,
    )
    def get(self, request, quiz_pk):
        principal = _principal(request)
        try:
            quiz = Quiz.objects.get(
                pk=quiz_pk, created_by_user_id=principal.erp_user_id
            )
        except Quiz.DoesNotExist as exc:
            raise NotFoundError("Quiz not found.") from exc

        qs = QuizAttempt.objects.filter(quiz=quiz).exclude(
            status="in_progress"
        )
        agg = qs.aggregate(
            avg_score=Avg("score"),
            max_score=Max("score"),
            min_score=Min("score"),
            total=Count("pk"),
            passed_count=Count("pk", filter=Q(passed=True)),
        )

        pass_pct = None
        if agg["total"]:
            pass_pct = round((agg["passed_count"] or 0) / agg["total"] * 100, 2)

        data = {
            "quiz_id": quiz.pk,
            "quiz_title": quiz.title,
            "total_submissions": agg["total"],
            "average_score": agg["avg_score"],
            "highest_score": agg["max_score"],
            "lowest_score": agg["min_score"],
            "pass_percentage": pass_pct,
            "submissions": qs.select_related("quiz").order_by("-submitted_at"),
        }
        return Response(s.QuizReportSerializer(data).data)


# ===========================================================================
# Student — Eligible Quizzes
# ===========================================================================

class EligibleQuizzesView(generics.GenericAPIView):
    permission_classes = [MODULE, P_VIEW]
    serializer_class = s.QuizListSerializer

    @extend_schema(
        operation_id="quiz_eligible_list",
        summary="List eligible quizzes for student",
        tags=["quiz"],
    )
    def get(self, request):
        qs = quiz_selectors.all_eligible_quizzes_for_student(_principal(request))
        return Response({"results": s.QuizListSerializer(qs, many=True).data})


class EligibleQuizDetailView(generics.GenericAPIView):
    permission_classes = [MODULE, P_VIEW]
    serializer_class = s.QuizDetailSerializer

    @extend_schema(
        operation_id="quiz_eligible_detail",
        summary="Eligible quiz detail + instructions",
        tags=["quiz"],
    )
    def get(self, request, pk):
        try:
            quiz = Quiz.objects.annotate(
                question_count=Count("questions", distinct=True),
                attempt_count=Count(
                    "attempts",
                    filter=Q(attempts__user_id=_principal(request).erp_user_id),
                    distinct=True,
                ),
            ).get(pk=pk)
        except Quiz.DoesNotExist as exc:
            raise NotFoundError("Quiz not found.") from exc
        return Response(s.QuizDetailSerializer(quiz).data)


class StartAttemptView(APIView):
    permission_classes = [MODULE, P_START]

    @extend_schema(
        operation_id="quiz_start_attempt",
        summary="Start a quiz attempt",
        tags=["quiz"],
        request=None,
        responses=s.AttemptDetailSerializer,
    )
    def post(self, request, pk):
        try:
            attempt = attempt_service.start_attempt(
                quiz_id=pk, principal=_principal(request)
            )
        except Quiz.DoesNotExist as exc:
            raise NotFoundError("Quiz not found.") from exc
        except QuizDomainError as exc:
            _map_domain_error(exc)
        return Response(
            s.AttemptDetailSerializer(attempt).data, status=status.HTTP_201_CREATED
        )


# ===========================================================================
# Student — Active Attempt
# ===========================================================================

class AttemptDetailView(generics.GenericAPIView):
    permission_classes = [MODULE, P_VIEW_OWN]
    serializer_class = s.AttemptDetailSerializer

    @extend_schema(
        operation_id="quiz_attempt_retrieve",
        summary="Get active attempt with questions",
        tags=["quiz"],
    )
    def get(self, request, pk):
        try:
            attempt = QuizAttempt.objects.select_related("quiz").prefetch_related(
                "responses__question", "quiz__questions"
            ).get(pk=pk, user_id=_principal(request).erp_user_id)
        except QuizAttempt.DoesNotExist as exc:
            raise NotFoundError("Attempt not found.") from exc
        return Response(s.AttemptDetailSerializer(attempt).data)


class SaveResponseView(APIView):
    permission_classes = [MODULE, P_START]

    @extend_schema(
        operation_id="quiz_save_response",
        summary="Save a response during active attempt",
        tags=["quiz"],
        request=s.SaveResponseSerializer,
        responses=s.SaveResponseResultSerializer,
    )
    def post(self, request, pk):
        payload = s.SaveResponseSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            attempt_service.save_response(
                attempt_id=pk,
                question_id=payload.validated_data["question_id"],
                response=payload.validated_data["response"],
                principal=_principal(request),
            )
        except QuizAttempt.DoesNotExist as exc:
            raise NotFoundError("Attempt not found.") from exc
        except QuizDomainError as exc:
            _map_domain_error(exc)
        return Response({"saved": True})


class SubmitAttemptView(APIView):
    permission_classes = [MODULE, P_START]

    @extend_schema(
        operation_id="quiz_submit_attempt",
        summary="Manually submit a quiz attempt",
        tags=["quiz"],
        request=None,
        responses=s.QuizAttemptSerializer,
    )
    def post(self, request, pk):
        try:
            attempt = attempt_service.submit_attempt(
                attempt_id=pk, principal=_principal(request)
            )
        except QuizAttempt.DoesNotExist as exc:
            raise NotFoundError("Attempt not found.") from exc
        except QuizDomainError as exc:
            _map_domain_error(exc)
        return Response(s.QuizAttemptSerializer(attempt).data)


# ===========================================================================
# Student — Results
# ===========================================================================

class MyResultsView(generics.GenericAPIView):
    permission_classes = [MODULE, P_VIEW_OWN]
    serializer_class = s.QuizAttemptSerializer

    @extend_schema(
        operation_id="quiz_my_results_list",
        summary="List student's released results",
        tags=["quiz"],
    )
    def get(self, request):
        qs = attempt_selectors.released_results(_principal(request))
        return Response({"results": s.QuizAttemptSerializer(qs, many=True).data})


class MyResultDetailView(generics.GenericAPIView):
    permission_classes = [MODULE, P_VIEW_OWN]
    serializer_class = s.AttemptDetailSerializer

    @extend_schema(
        operation_id="quiz_my_result_detail",
        summary="Single released result with responses",
        tags=["quiz"],
    )
    def get(self, request, pk):
        try:
            attempt = QuizAttempt.objects.select_related("quiz").prefetch_related(
                "responses__question", "quiz__questions"
            ).get(
                pk=pk,
                user_id=_principal(request).erp_user_id,
                status="released",
            )
        except QuizAttempt.DoesNotExist as exc:
            raise NotFoundError("Result not found or not yet released.") from exc
        return Response(s.AttemptDetailSerializer(attempt).data)
