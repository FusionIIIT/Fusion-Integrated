"""Quiz domain errors — pure Python, no Django imports."""


class QuizDomainError(Exception):
    """Base class for quiz domain errors."""


class InvalidQuizTransition(QuizDomainError):
    """A quiz state transition that the state machine does not permit."""


class InvalidAttemptTransition(QuizDomainError):
    """An attempt state transition that is not allowed."""


class AttemptLimitExceeded(QuizDomainError):
    """Student has used all permitted attempts for this quiz."""


class QuizNotAvailable(QuizDomainError):
    """Quiz is not in Available state or outside availability window."""


class AttemptNotActive(QuizDomainError):
    """Attempt is not in In Progress state."""


class AttemptAlreadySubmitted(QuizDomainError):
    """Attempt is already submitted and immutable."""


class QuizNotEditable(QuizDomainError):
    """Quiz cannot be edited after activation."""


class EvaluationError(QuizDomainError):
    """Evaluation could not be completed."""
