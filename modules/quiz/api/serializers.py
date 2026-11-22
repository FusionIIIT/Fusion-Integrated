from rest_framework import serializers

from modules.quiz.models import (
    AttemptResponse,
    QuestionBankItem,
    Quiz,
    QuizAttempt,
    QuizOption,
    QuizQuestion,
    QuizResult,
    QuizSettings,
    ResponseEvaluation,
)


class QuizSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizSettings
        fields = [
            "allow_unanswered",
            "back_navigation",
            "tab_violation_limit",
            "negative_marking_enabled",
            "result_visibility",
        ]


class QuizOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizOption
        fields = ["id", "option_id", "option_text"]


class QuizQuestionSerializer(serializers.ModelSerializer):
    options = QuizOptionSerializer(many=True, read_only=True)

    class Meta:
        model = QuizQuestion
        fields = [
            "id",
            "quiz_id",
            "question_text",
            "question_type",
            "marks",
            "negative_marks",
            "correct",
            "position",
            "options",
        ]


class QuizListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quiz
        fields = [
            "id",
            "course_id",
            "title",
            "instructions",
            "status",
            "duration_minutes",
            "max_attempts",
            "start_at",
            "close_at",
            "created_at",
        ]


class QuizDetailSerializer(serializers.ModelSerializer):
    settings = QuizSettingsSerializer(read_only=True)
    questions = QuizQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = [
            "id",
            "course_id",
            "title",
            "instructions",
            "status",
            "duration_minutes",
            "max_attempts",
            "start_at",
            "close_at",
            "settings",
            "questions",
            "created_at",
        ]


class QuestionBankItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionBankItem
        fields = [
            "id",
            "owner_user_id",
            "question_text",
            "question_type",
            "topic",
            "difficulty",
            "marks",
            "negative_marks",
            "image",
            "created_at",
        ]
        read_only_fields = ["owner_user_id", "created_at"]


class AttemptResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttemptResponse
        fields = ["id", "attempt_id", "question_id", "answer", "saved_at"]


class ResponseEvaluationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResponseEvaluation
        fields = [
            "id",
            "response_id",
            "status",
            "auto_marks",
            "final_marks",
            "feedback",
            "finalized_by",
        ]


class QuizResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizResult
        fields = ["id", "attempt_id", "status", "marks_obtained", "percentage", "passed"]


class QuizAttemptSerializer(serializers.ModelSerializer):
    responses = AttemptResponseSerializer(many=True, read_only=True)
    result = QuizResultSerializer(read_only=True)

    class Meta:
        model = QuizAttempt
        fields = [
            "id",
            "quiz_id",
            "student_id",
            "status",
            "deadline_at",
            "tab_violations",
            "submitted_at",
            "responses",
            "result",
            "created_at",
        ]
