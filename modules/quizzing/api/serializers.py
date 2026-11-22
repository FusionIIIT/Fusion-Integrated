"""Serializers for Quizzing endpoints with field-level scoping and masking."""

from rest_framework import serializers

from modules.quizzing.models import (
    AttemptIntegrityLog,
    Question,
    Quiz,
    QuizAttempt,
    QuizQuestion,
    StudentAnswer,
)


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = [
            "id",
            "question_text",
            "question_type",
            "difficulty",
            "options",
            "default_marks",
            "negative_marks",
            "correct_answer",
        ]
        read_only_fields = ["id"]


class QuizQuestionSerializer(serializers.ModelSerializer):
    question = QuestionSerializer(read_only=True)

    class Meta:
        model = QuizQuestion
        fields = ["id", "question", "order", "marks"]
        read_only_fields = ["id", "marks"]


class QuizListSerializer(serializers.ModelSerializer):
    question_count = serializers.IntegerField(source="quiz_questions.count", read_only=True)

    class Meta:
        model = Quiz
        fields = [
            "id",
            "course_code",
            "title",
            "description",
            "start_time",
            "end_time",
            "duration_minutes",
            "status",
            "total_marks",
            "passing_marks",
            "max_attempts",
            "navigation_mode",
            "randomize_questions",
            "allow_unanswered",
            "answer_key_released",
            "grades_released",
            "question_count",
        ]
        read_only_fields = fields


class QuizDetailSerializer(serializers.ModelSerializer):
    questions = QuizQuestionSerializer(source="quiz_questions", many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = [
            "id",
            "course_code",
            "title",
            "description",
            "created_by",
            "start_time",
            "end_time",
            "duration_minutes",
            "status",
            "total_marks",
            "passing_marks",
            "max_attempts",
            "navigation_mode",
            "randomize_questions",
            "allow_unanswered",
            "answer_key_released",
            "grades_released",
            "questions",
        ]
        read_only_fields = fields

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        request = self.context.get("request")
        is_faculty = False
        if request and hasattr(request, "user"):
            is_faculty = instance.created_by == getattr(request.user, "username", "")

        # Mask question solutions for students until answer key is released
        if not is_faculty and not instance.answer_key_released and "questions" in ret:
            for q_wrap in ret["questions"]:
                if "question" in q_wrap and "correct_answer" in q_wrap["question"]:
                    q_wrap["question"]["correct_answer"] = {}
        return ret


class StudentAnswerSerializer(serializers.ModelSerializer):
    final_score = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)

    class Meta:
        model = StudentAnswer
        fields = [
            "id",
            "question_id",
            "submitted_answer",
            "autograded_score",
            "override_score",
            "final_score",
            "feedback",
            "is_evaluated",
        ]
        read_only_fields = ["id", "autograded_score", "override_score", "final_score", "is_evaluated"]

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        request = self.context.get("request")
        attempt = instance.attempt
        is_faculty = False
        if request and hasattr(request, "user"):
            is_faculty = attempt.quiz.created_by == getattr(request.user, "username", "")

        # Mask individual scores and feedback for students until grades released
        if not is_faculty and not attempt.quiz.grades_released:
            ret["autograded_score"] = None
            ret["override_score"] = None
            ret["final_score"] = None
            ret["feedback"] = ""
        return ret


class QuizAttemptSerializer(serializers.ModelSerializer):
    answers = StudentAnswerSerializer(many=True, read_only=True)
    quiz_title = serializers.CharField(source="quiz.title", read_only=True)
    course_code = serializers.CharField(source="quiz.course_code", read_only=True)

    class Meta:
        model = QuizAttempt
        fields = [
            "id",
            "quiz_id",
            "quiz_title",
            "course_code",
            "student_user_id",
            "attempt_number",
            "started_at",
            "submitted_at",
            "status",
            "total_score",
            "passed",
            "flagged_for_integrity",
            "answers",
        ]
        read_only_fields = fields

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        request = self.context.get("request")
        is_faculty = False
        if request and hasattr(request, "user"):
            is_faculty = instance.quiz.created_by == getattr(request.user, "username", "")

        # Mask overall result details for students until instructor releases grades
        if not is_faculty and not instance.quiz.grades_released:
            ret["total_score"] = None
            ret["passed"] = None
        return ret


class AttemptIntegrityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttemptIntegrityLog
        fields = ["id", "attempt_id", "event_type", "timestamp", "details"]
        read_only_fields = ["id", "timestamp"]
