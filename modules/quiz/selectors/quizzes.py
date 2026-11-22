def list_quizzes(user_id, role, course_id=None):
    from modules.quiz.selectors.scoping import scope_quizzes_for_user

    return scope_quizzes_for_user(user_id, role, course_id)


def get_quiz_by_id(quiz_id, user_id, role):
    from modules.quiz.selectors.scoping import get_scoped_quiz

    return get_scoped_quiz(quiz_id, user_id, role)
