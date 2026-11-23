class IllegalTransition(Exception):
    """A state change the transition table does not allow."""


class RuleViolation(Exception):
    """A business rule refused the action; the message says what to do next."""
