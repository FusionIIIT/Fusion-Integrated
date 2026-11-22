"""API views handling HTTP transport, permission enforcement, and status mapping."""

from decimal import Decimal

from rest_framework import permissions, status, views
from rest_framework.response import Response

from modules.quizzing.domain.rules import DomainRuleError
from modules.quizzing.domain.state_machine import InvalidStateTransitionError
from modules.quizzing.models import Quiz, QuizAttempt, StudentAnswer
from modules.quizzing.selectors.quiz_selectors import (
    get_attempt_for_actor,
    get_attempt_integrity_logs,
    get_faculty_quizzes,
    get_question_banks,
    get_questions_for_bank,
    get_quiz_attempts_for_grading,
    get_quiz_for_actor,
    get_quiz_performance_metrics,
    get_student_quizzes,
)
from modules.quizzing.services.quiz_service import QuizService

from .serializers import (
    AttemptIntegrityLogSerializer,
    QuestionBankSerializer,
    QuestionSerializer,
    QuizAttemptSerializer,
    QuizDetailSerializer,
    QuizListSerializer,
    StudentAnswerSerializer,
)


def get_actor_username(request) -> str:
    user = getattr(request, "user", None)
    return str(getattr(user, "username", user)) if user else "anon"


def check_has_permission(request, perm_code: str) -> bool:
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return False
    if hasattr(user, "has_perm") and user.has_perm(perm_code):
        return True
    active_role = getattr(user, "active_role", "")
    if active_role in ["faculty", "professor"] and perm_code in [
        "quizzing.quiz.view",
        "quizzing.quiz.author",
        "quizzing.quiz.grade",
    ]:
        return True
    return bool(
        active_role == "student"
        and perm_code in ["quizzing.quiz.view", "quizzing.quiz.attempt"]
    )


class QuestionBankListCreateView(views.APIView):
    """Question bank management and search API for professors (AFR-QZ-005.2)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not check_has_permission(request, "quizzing.quiz.author"):
            return Response({"error": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
        actor_id = get_actor_username(request)
        banks = get_question_banks(faculty_id=actor_id)
        query = request.query_params.get("search", "").strip()
        if query:
            banks = banks.filter(title__icontains=query)
        return Response(QuestionBankSerializer(banks, many=True).data)

    def post(self, request):
        if not check_has_permission(request, "quizzing.quiz.author"):
            return Response({"error": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
        d = request.data
        bank = QuizService.create_question_bank(
            course_code=d["course_code"],
            title=d["title"],
            created_by=get_actor_username(request),
            description=d.get("description", ""),
        )
        return Response(QuestionBankSerializer(bank).data, status=status.HTTP_201_CREATED)


class QuestionBankQuestionView(views.APIView):
    """View to search, filter, and create questions within a question bank."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        if not check_has_permission(request, "quizzing.quiz.author"):
            return Response({"error": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
        questions = get_questions_for_bank(str(pk))
        q_type = request.query_params.get("type")
        if q_type:
            questions = questions.filter(question_type=q_type)
        return Response(QuestionSerializer(questions, many=True).data)

    def post(self, request, pk):
        if not check_has_permission(request, "quizzing.quiz.author"):
            return Response({"error": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
        d = request.data
        q = QuizService.create_question(
            bank_id=str(pk),
            question_text=d["question_text"],
            question_type=d["question_type"],
            options=d.get("options", []),
            correct_answer=d.get("correct_answer", {}),
            default_marks=Decimal(str(d.get("default_marks", "1.0"))),
            negative_marks=Decimal(str(d.get("negative_marks", "0.0"))),
            difficulty=d.get("difficulty", "MEDIUM"),
        )
        return Response(QuestionSerializer(q).data, status=status.HTTP_201_CREATED)


class QuizListCreateView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        actor_id = get_actor_username(request)
        mode = request.query_params.get("mode", "student")
        if mode == "faculty":
            if not check_has_permission(request, "quizzing.quiz.author"):
                return Response(
                    {"error": "Permission denied to view faculty quiz management."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            quizzes = get_faculty_quizzes(actor_id)
        else:
            quizzes = get_student_quizzes(actor_id)
        return Response(QuizListSerializer(quizzes, many=True).data)

    def post(self, request):
        if not check_has_permission(request, "quizzing.quiz.author"):
            return Response(
                {"error": "Only faculty members can author and create quizzes."},
                status=status.HTTP_403_FORBIDDEN,
            )

        d = request.data
        try:
            quiz = QuizService.create_quiz(
                title=d["title"],
                course_code=d["course_code"],
                created_by=get_actor_username(request),
                start_time=d["start_time"],
                end_time=d["end_time"],
                duration_minutes=int(d["duration_minutes"]),
                description=d.get("description", ""),
                passing_marks=Decimal(str(d.get("passing_marks", "0.0"))),
                max_attempts=int(d.get("max_attempts", 1)),
                navigation_mode=d.get("navigation_mode", "FREE"),
                randomize_questions=bool(d.get("randomize_questions", False)),
                allow_unanswered=bool(d.get("allow_unanswered", True)),
                negative_marking_percentage=Decimal(
                    str(d.get("negative_marking_percentage", "0.0"))
                ),
                question_ids=d.get("question_ids", []),
            )
            return Response(
                QuizDetailSerializer(quiz, context={"request": request}).data,
                status=status.HTTP_201_CREATED,
            )
        except DomainRuleError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except (KeyError, ValueError) as e:
            msg = f"Invalid parameter: {e}"
            return Response({"error": msg}, status=status.HTTP_400_BAD_REQUEST)


class QuizDetailView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        actor_id = get_actor_username(request)
        is_faculty = check_has_permission(request, "quizzing.quiz.author")
        try:
            quiz = get_quiz_for_actor(str(pk), actor_id, is_faculty=is_faculty)
            return Response(QuizDetailSerializer(quiz, context={"request": request}).data)
        except Quiz.DoesNotExist:
            return Response({"error": "Quiz not found."}, status=status.HTTP_404_NOT_FOUND)


class QuizActionView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk, action):
        actor_id = get_actor_username(request)
        try:
            if action == "publish":
                if not check_has_permission(request, "quizzing.quiz.author"):
                    return Response({"error": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
                quiz = QuizService.publish_quiz(str(pk), actor_id=actor_id)
                return Response(QuizDetailSerializer(quiz, context={"request": request}).data)

            if action == "close":
                if not check_has_permission(request, "quizzing.quiz.author"):
                    return Response({"error": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
                quiz = QuizService.close_quiz(str(pk), actor_id=actor_id)
                return Response(QuizDetailSerializer(quiz, context={"request": request}).data)

            if action == "archive":
                if not check_has_permission(request, "quizzing.quiz.author"):
                    return Response({"error": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
                quiz = QuizService.archive_quiz(str(pk), actor_id=actor_id)
                return Response(QuizDetailSerializer(quiz, context={"request": request}).data)

            if action == "start":
                if not check_has_permission(request, "quizzing.quiz.attempt"):
                    return Response({"error": "Students only."}, status=status.HTTP_403_FORBIDDEN)
                attempt = QuizService.start_attempt(str(pk), student_id=actor_id)
                return Response(
                    QuizAttemptSerializer(attempt, context={"request": request}).data,
                    status=status.HTTP_201_CREATED,
                )

            if action in ["release-key", "release-grades"]:
                if not check_has_permission(request, "quizzing.quiz.grade"):
                    return Response({"error": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
                field = "answer_key_released" if action == "release-key" else "grades_released"
                val = bool(request.data.get("release", True))
                quiz = QuizService.toggle_release(
                    quiz_id=str(pk),
                    faculty_id=actor_id,
                    field=field,
                    value=val,
                )
                return Response(QuizDetailSerializer(quiz, context={"request": request}).data)

            return Response(
                {"error": f"Unsupported action: {action}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Quiz.DoesNotExist:
            return Response({"error": "Quiz not found."}, status=status.HTTP_404_NOT_FOUND)
        except PermissionError as e:
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except InvalidStateTransitionError as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)
        except DomainRuleError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class QuizAttemptDetailView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        actor_id = get_actor_username(request)
        is_faculty = check_has_permission(request, "quizzing.quiz.grade")
        try:
            attempt = get_attempt_for_actor(str(pk), actor_id, is_faculty=is_faculty)
            return Response(QuizAttemptSerializer(attempt, context={"request": request}).data)
        except QuizAttempt.DoesNotExist:
            return Response({"error": "Attempt not found."}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request, pk):
        actor_id = get_actor_username(request)
        action = request.data.get("action", "save")
        try:
            if action == "save":
                if not check_has_permission(request, "quizzing.quiz.attempt"):
                    return Response({"error": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
                ans = QuizService.save_answer(
                    attempt_id=str(pk),
                    arg2=actor_id,
                    arg3=request.data["question_id"],
                    arg4=request.data["submitted_answer"],
                )
                return Response(StudentAnswerSerializer(ans, context={"request": request}).data)

            if action == "submit":
                if not check_has_permission(request, "quizzing.quiz.attempt"):
                    return Response({"error": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
                attempt = QuizService.submit_attempt(
                    attempt_id=str(pk),
                    student_id=actor_id,
                    autosubmit=bool(request.data.get("autosubmit", False)),
                )
                return Response(QuizAttemptSerializer(attempt, context={"request": request}).data)

            if action == "integrity":
                log_entry = QuizService.log_integrity_event(
                    attempt_id=str(pk),
                    student_id=actor_id,
                    event_type=request.data["event_type"],
                    details=request.data.get("details", ""),
                )
                return Response(
                    AttemptIntegrityLogSerializer(log_entry).data,
                    status=status.HTTP_201_CREATED,
                )

            return Response(
                {"error": f"Invalid attempt action: {action}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except QuizAttempt.DoesNotExist:
            return Response({"error": "Attempt not found."}, status=status.HTTP_404_NOT_FOUND)
        except PermissionError as e:
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except DomainRuleError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except KeyError as e:
            msg = f"Missing required parameter: {e}"
            return Response({"error": msg}, status=status.HTTP_400_BAD_REQUEST)


class QuizGradingView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        if not check_has_permission(request, "quizzing.quiz.grade"):
            return Response({"error": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
        actor_id = get_actor_username(request)
        try:
            attempts = get_quiz_attempts_for_grading(str(pk), faculty_id=actor_id)
            serializer = QuizAttemptSerializer(attempts, many=True, context={"request": request})
            return Response(serializer.data)
        except Quiz.DoesNotExist:
            return Response({"error": "Quiz not found."}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request, pk):
        if not check_has_permission(request, "quizzing.quiz.grade"):
            return Response({"error": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
        actor_id = get_actor_username(request)
        try:
            ans = QuizService.override_score(
                answer_id=str(pk),
                faculty_id=actor_id,
                override_score=Decimal(str(request.data["override_score"])),
                feedback=request.data.get("feedback", ""),
            )
            return Response(StudentAnswerSerializer(ans, context={"request": request}).data)
        except StudentAnswer.DoesNotExist:
            return Response(
                {"error": "Answer record not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except PermissionError as e:
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except KeyError as e:
            msg = f"Missing required parameter: {e}"
            return Response({"error": msg}, status=status.HTTP_400_BAD_REQUEST)


class QuizAnalyticsReportView(views.APIView):
    """Aggregate quiz performance analytics and reports for instructors (AFR-QZ-015.2)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        if not check_has_permission(request, "quizzing.quiz.grade"):
            return Response({"error": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
        actor_id = get_actor_username(request)
        try:
            metrics = get_quiz_performance_metrics(str(pk), faculty_id=actor_id)
            return Response(metrics)
        except Quiz.DoesNotExist:
            return Response({"error": "Quiz not found."}, status=status.HTTP_404_NOT_FOUND)


class AiEvaluationView(views.APIView):
    """Advisory AI subjective evaluation endpoint (AFR-QZ-012.2)."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        if not check_has_permission(request, "quizzing.quiz.grade"):
            return Response({"error": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
        actor_id = get_actor_username(request)
        try:
            suggestion = QuizService.request_ai_evaluation(answer_id=str(pk), faculty_id=actor_id)
            return Response(suggestion)
        except StudentAnswer.DoesNotExist:
            return Response(
                {"error": "Answer record not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except PermissionError as e:
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)


class AttemptIntegrityLogsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        actor_id = get_actor_username(request)
        is_faculty = check_has_permission(request, "quizzing.quiz.grade")
        try:
            logs = get_attempt_integrity_logs(str(pk), actor_id=actor_id, is_faculty=is_faculty)
            return Response(AttemptIntegrityLogSerializer(logs, many=True).data)
        except QuizAttempt.DoesNotExist:
            return Response({"error": "Attempt not found."}, status=status.HTTP_404_NOT_FOUND)
