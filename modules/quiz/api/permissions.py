"""Custom DRF permission classes for the quiz module."""

from fusion_auth.permissions import HasPermission

IsProfessor = HasPermission("quiz.quiz.manage")
IsStudentOrProfessor = HasPermission("quiz.quiz.view")
CanStartAttempt = HasPermission("quiz.attempt.start")
CanViewOwnAttempts = HasPermission("quiz.attempt.view_own")
CanEvaluate = HasPermission("quiz.evaluation.manage")
CanViewReports = HasPermission("quiz.report.view")
