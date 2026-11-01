from fusion_auth.permissions import HasModuleGrant, HasPermission

QUIZ_MANAGE = "quiz.manage"
QUESTION_BANK_MANAGE = "quiz.question_bank.manage"
QUIZ_EVALUATE = "quiz.evaluate"
QUIZ_RELEASE = "quiz.release"
QUIZ_REPORT_VIEW = "quiz.report.view"
QUIZ_ATTEMPT = "quiz.attempt"
RESULT_VIEW_OWN = "quiz.result.view_own"
HISTORY_VIEW_OWN = "quiz.history.view_own"

MODULE = HasModuleGrant("quiz")


def permission_classes(*permissions: str):
    """Return the standard module gate followed by an all-permissions gate."""
    return [MODULE, HasPermission(*permissions, require_all=True)]
