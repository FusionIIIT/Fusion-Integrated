from modules.oap.models import OAPApplication, OAPServiceRequest, OAPServiceOutcome



class OAPApplicationEntity:

    def __init__(self, application: OAPApplication):

        self.application = application



    @property

    def user_id(self) -> int:

        return self.application.user_id



    @property

    def application_date(self) -> str:

        return self.application.application_date.strftime("%Y-%m-%d")



    @property

    def application_details(self) -> dict:

        return self.application.application_details



    @property

    def status(self) -> str:

        return self.application.status



    @property

    def submitted_by(self) -> int:

        return self.application.submitted_by.user_id if self.application.submitted_by else None



    @property

    def reviewed_by(self) -> int:

        return self.application.reviewed_by.user_id if self.application.reviewed_by else None





class OAPServiceRequestEntity:

    def __init__(self, request: OAPServiceRequest):

        self.request = request



    @property

    def application_id(self) -> int:

        return self.request.application_id



    @property

    def service_type(self) -> str:

        return self.request.service_type



    @property

    def service_details(self) -> dict:

        return self.request.service_details



    @property

    def status(self) -> str:

        return self.request.status



    @property

    def requested_by(self) -> int:

        return self.request.requested_by.user_id if self.request.requested_by else None



    @property

    def assigned_to(self) -> int:

        return self.request.assigned_to.user_id if self.request.assigned_to else None





class OAPServiceOutcomeEntity:

    def __init__(self, outcome: OAPServiceOutcome):

        self.outcome = outcome



    @property

    def service_request_id(self) -> int:

        return self.outcome.service_request_id



    @property

    def outcome_details(self) -> dict:

        return self.outcome.outcome_details



    @property

    def completed_at(self) -> str:

        return self.outcome.completed_at.strftime("%Y-%m-%d %H:%M:%S") if self.outcome.completed_at else None



    @property

    def completed_by(self) -> int:

        return self.outcome.completed_by.user_id if self.outcome.completed_by else None