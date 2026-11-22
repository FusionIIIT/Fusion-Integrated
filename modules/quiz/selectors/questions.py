from modules.quiz.models import QuestionBankItem, QuizQuestion


def search_question_bank(owner_user_id, topic=None, difficulty=None, question_type=None):
    qs = QuestionBankItem.objects.filter(owner_user_id=owner_user_id)
    if topic:
        qs = qs.filter(topic__icontains=topic)
    if difficulty:
        qs = qs.filter(difficulty=difficulty)
    if question_type:
        qs = qs.filter(question_type=question_type)
    return qs.order_by("-created_at")


def get_quiz_questions(quiz_id):
    return (
        QuizQuestion.objects.filter(quiz_id=quiz_id)
        .prefetch_related("options")
        .order_by("position")
    )
