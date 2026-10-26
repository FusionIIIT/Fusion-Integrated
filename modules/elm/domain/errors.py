class RuleViolation(Exception):
    """A business rule refused the request. Carries the rule id for the audit."""

    def __init__(self, message: str, rule: str = ""):
        super().__init__(message)
        self.rule = rule
