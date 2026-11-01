# modules/quiz/registry.py
from fusion_auth.registry import MODULE, NAV_ITEM, ROLE_GRANT, SYSTEM_PERMISSION

MODULE = MODULE(
    code="quiz",
    label="Quiz",
    icon="FaQuiz",
    base_path="/quiz",
    nav_section="Academics",
    sort_order=400,
    status="planned",
    legacy_column_name="quiz_management"
)

NAV_ITEMS = [
    NAV_ITEM(
        code="quiz.list",
        label="Quiz List",
        icon="FaListUl",
        path="/quiz/list",
        required_permission="quiz.quiz.view"
    ),
    NAV_ITEM(
        code="quiz.create",
        label="Create Quiz",
        icon="FaPlus",
        path="/quiz/create",
        required_permission="quiz.quiz.create"
    ),
    NAV_ITEM(
        code="question.list",
        label="Question List",
        icon="FaListUl",
        path="/quiz/questions",
        required_permission="quiz.question.view"
    ),
    NAV_ITEM(
        code="question.create",
        label="Create Question",
        icon="FaPlus",
        path="/quiz/questions/create",
        required_permission="quiz.question.create"
    )
]

ROLE_GRANTS = {
    "professor": ["quiz.quiz.create", "quiz.quiz.view", "quiz.quiz.edit", "quiz.quiz.delete"],
    "student": ["quiz.quiz.view"]
}

SYSTEM_PERMISSIONS = []
