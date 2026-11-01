from rest_framework import status, views, permissions
from rest_framework.response import Response
from modules.quizzing.selectors.quiz_selectors import (
    get_student_quizzes, get_faculty_quizzes, get_quiz_by_id, get_attempt_by_id,
    get_quiz_attempts_for_grading, get_attempt_integrity_logs,
)
from modules.quizzing.services.quiz_service import QuizService
from .serializers import (
    QuizListSerializer, QuizDetailSerializer, QuizAttemptSerializer,
    StudentAnswerSerializer, AttemptIntegrityLogSerializer,
)


def actor(request) -> str:
    return str(getattr(request.user, "username", request.user)) if getattr(request, "user", None) else "anon"


class QuizListCreateView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        mode = request.query_params.get("mode", "student")
        qs = get_faculty_quizzes(actor(request)) if mode == "faculty" else get_student_quizzes(actor(request))
        return Response(QuizListSerializer(qs, many=True).data)

    def post(self, request):
        d = request.data
        try:
            quiz = QuizService.create_quiz(
                title=d["title"], course_code=d["course_code"], created_by=actor(request),
                start_time=d["start_time"], end_time=d["end_time"], duration_minutes=int(d["duration_minutes"]),
                description=d.get("description", ""), question_ids=d.get("question_ids", []),
            )
            return Response(QuizDetailSerializer(quiz).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class QuizDetailView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            return Response(QuizDetailSerializer(get_quiz_by_id(pk)).data)
        except Exception:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)


class QuizActionView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk, action):
        try:
            if action == "publish":
                return Response(QuizDetailSerializer(QuizService.publish_quiz(pk)).data)
            if action == "start":
                return Response(QuizAttemptSerializer(QuizService.start_attempt(pk, actor(request))).data, status=status.HTTP_201_CREATED)
            if action in ["release-key", "release-grades"]:
                field = "answer_key_released" if action == "release-key" else "grades_released"
                return Response(QuizDetailSerializer(QuizService.toggle_release(pk, field, request.data.get("release", True))).data)
            return Response({"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class QuizAttemptDetailView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        return Response(QuizAttemptSerializer(get_attempt_by_id(pk)).data)

    def post(self, request, pk):
        action = request.data.get("action", "save")
        try:
            if action == "save":
                return Response(StudentAnswerSerializer(QuizService.save_answer(pk, request.data["question_id"], request.data["submitted_answer"])).data)
            if action == "submit":
                return Response(QuizAttemptSerializer(QuizService.submit_attempt(pk, request.data.get("autosubmit", False))).data)
            if action == "integrity":
                return Response(AttemptIntegrityLogSerializer(QuizService.log_integrity_event(pk, request.data["event_type"], request.data.get("details", ""))).data, status=status.HTTP_201_CREATED)
            return Response({"error": "Bad action"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class QuizGradingView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        return Response(QuizAttemptSerializer(get_quiz_attempts_for_grading(pk), many=True).data)

    def post(self, request, pk):
        try:
            ans = QuizService.override_score(pk, request.data["override_score"], request.data.get("feedback", ""))
            return Response(StudentAnswerSerializer(ans).data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AttemptIntegrityLogsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        return Response(AttemptIntegrityLogSerializer(get_attempt_integrity_logs(pk), many=True).data)
