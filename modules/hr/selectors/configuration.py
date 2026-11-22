from django.db.models import QuerySet

from modules.hr.models import AppraisalWindow, WorkflowRoute


def workflow_routes() -> QuerySet[WorkflowRoute]:
    return WorkflowRoute.objects.all()


def appraisal_windows() -> QuerySet[AppraisalWindow]:
    return AppraisalWindow.objects.all()
