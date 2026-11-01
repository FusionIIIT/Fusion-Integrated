class OAPError(Exception):

    """Base class for OAP domain errors."""



    def __init__(self, message: str, code: str):

        super().__init__(message)

        self.code = code





class InvalidApplicationStatusError(OAPError):

    """Error raised when an invalid status is encountered for an application."""



    def __init__(self, status: str):

        super().__init__(f"Invalid application status: {status}", "INVALID_STATUS")





class InvalidServiceRequestStatusError(OAPError):

    """Error raised when an invalid status is encountered for a service request."""



    def __init__(self, status: str):

        super().__init__(f"Invalid service request status: {status}", "INVALID_STATUS")





class InvalidServiceOutcomeStatusError(OAPError):

    """Error raised when an invalid status is encountered for a service outcome."""



    def __init__(self, status: str):

        super().__init__(f"Invalid service outcome status: {status}", "INVALID_STATUS")