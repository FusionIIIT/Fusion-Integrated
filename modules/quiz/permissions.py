# modules/quiz/permissions.py
MODULE_CODE = "quiz"

PERMISSIONS = [
    P("quiz.quiz.create", "Create a quiz"),
    P("quiz.quiz.view", "View quizzes"),
    P("quiz.quiz.edit", "Edit a quiz"),
    P("quiz.quiz.delete", "Delete a quiz"),
    P("quiz.question.create", "Create a question"),
    P("quiz.question.view", "View questions"),
    P("quiz.question.edit", "Edit a question"),
    P("quiz.question.delete", "Delete a question"),
]
