from modules.oap.domain.entities import OAPApplicationEntity, OAPServiceRequestEntity, OAPServiceOutcomeEntity
from modules.oap.domain.errors import InvalidApplicationStatusError, InvalidServiceRequestStatusError, InvalidServiceOutcomeStatusError

class OAPApplicationStateMachine:
    STATUS_TRANSITIONS = {
        "draft": ["submitted"],
        "submitted": ["under_review", "rejected"],
        "under_review": ["approved", "rejected"],
        "approved": [],
        "rejected": [],
    }

    @staticmethod
    def transition(application: OAPApplicationEntity, to_status: str):
        if application.status not in OAPApplicationStateMachine.STATUS_TRANSITIONS:
            raise InvalidApplicationStatusError(application.status)

        if to_status not in OAPApplicationStateMachine.STATUS_TRANSITIONS[application.status]:
            raise InvalidApplicationStatusError(to_status)

        application.application.status = to_status
        application.application.save()


class OAPServiceRequestStateMachine:
    STATUS_TRANSITIONS = {
        "pending": ["in_progress", "cancelled"],
        "in_progress": ["completed"],
        "completed": [],
        "cancelled": [],
    }

    @staticmethod
    def transition(request: OAPServiceRequestEntity, to_status: str):
        if request.status not in OAPServiceRequestStateMachine.STATUS_TRANSITIONS:
            raise InvalidServiceRequestStatusError(request.status)

        if to_status not in OAPServiceRequestStateMachine.STATUS_TRANSITIONS[request.status]:
            raise InvalidServiceRequestStatusError(to_status)

        request.request.status = to_status
        request.request.save()


class OAPServiceOutcomeStateMachine:
    STATUS_TRANSITIONS = {
        "pending": ["completed"],
        "completed": [],
    }

    @staticmethod
    def transition(outcome: OAPServiceOutcomeEntity, to_status: str):
        if outcome.status not in OAPServiceOutcomeStateMachine.STATUS_TRANSITIONS:
            raise InvalidServiceOutcomeStatusError(outcome.status)

        if to_status not in OAPServiceOutcomeStateMachine.STATUS_TRANSITIONS[outcome.status]:
            raise InvalidOutcomeStatusError(to_status)

        outcome.outcome.status = to_status
        outcome.outcome.save()
