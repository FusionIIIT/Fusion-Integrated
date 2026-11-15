from rest_framework import serializers
from modules.quizzing.models import Question, Quiz, QuizQuestion, QuizAttempt, StudentAnswer, AttemptIntegrityLog


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ["id", "question_text", "question_type", "difficulty", "options", "correct_answer", "default_marks"]


class QuizQuestionSerializer(serializers.ModelSerializer):
    question = QuestionSerializer(read_only=True)

    class Meta:
        model = QuizQuestion
        fields = ["id", "order", "marks", "question"]


class QuizListSerializer(serializers.ModelSerializer):
    question_count = serializers.IntegerField(source="quiz_questions.count", read_only=True)

    class Meta:
        model = Quiz
        fields = ["id", "title", "course_code", "created_by", "start_time", "end_time", "duration_minutes", "status", "total_marks", "answer_key_released", "grades_released", "question_count"]


class QuizDetailSerializer(serializers.ModelSerializer):
    questions = QuizQuestionSerializer(source="quiz_questions", many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = ["id", "title", "description", "course_code", "created_by", "start_time", "end_time", "duration_minutes", "status", "total_marks", "answer_key_released", "grades_released", "questions"]


class StudentAnswerSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source="question.question_text", read_only=True)

    class Meta:
        model = StudentAnswer
        fields = ["id", "question", "question_text", "submitted_answer", "autograded_score", "override_score", "final_score", "feedback"]


class QuizAttemptSerializer(serializers.ModelSerializer):
    answers = StudentAnswerSerializer(many=True, read_only=True)
    quiz_title = serializers.CharField(source="quiz.title", read_only=True)
    quiz_duration = serializers.IntegerField(source="quiz.duration_minutes", read_only=True)

    class Meta:
        model = QuizAttempt
        fields = ["id", "quiz", "quiz_title", "quiz_duration", "student_user_id", "started_at", "submitted_at", "status", "total_score", "answers"]


class AttemptIntegrityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttemptIntegrityLog
        fields = ["id", "event_type", "timestamp", "details"]
