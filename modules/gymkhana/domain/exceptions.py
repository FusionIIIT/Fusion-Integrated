"""Pure-Python domain exceptions. No framework dependencies."""


class GymkhanaDomainError(Exception):
    """Base domain error for Gymkhana."""


class InvalidTransition(GymkhanaDomainError):
    def __init__(self, machine: str, frm: str | None, to: str, reason: str = ""):
        msg = f"Cannot transition {machine} from {frm!r} to {to!r}."
        if reason:
            msg += f" Reason: {reason}"
        super().__init__(msg)
        self.machine = machine
        self.frm = frm
        self.to = to
        self.reason = reason


class ActorNotAllowed(GymkhanaDomainError):
    def __init__(self, machine: str, actor: str, event: str):
        super().__init__(f"Actor {actor!r} is not authorized to trigger {event!r} on {machine}.")
        self.machine = machine
        self.actor = actor
        self.event = event


class GuardFailed(GymkhanaDomainError):
    def __init__(self, guard: str, message: str = ""):
        super().__init__(message or f"Guard condition {guard!r} failed.")
        self.guard = guard


class InvalidVenueError(GymkhanaDomainError):
    def __init__(self, venue: str):
        super().__init__(f"Venue {venue!r} is not configured for Gymkhana booking.")
        self.venue = venue


class InvalidTimeRangeError(GymkhanaDomainError):
    def __init__(self, message: str = "Booking start time must be strictly earlier than end time."):
        super().__init__(message)


class InvalidPollChoicesError(GymkhanaDomainError):
    def __init__(self, message: str = "A voting poll must have at least two choices."):
        super().__init__(message)


class InvalidVoteChoiceError(GymkhanaDomainError):
    def __init__(self, message: str = "Selected choice does not belong to the target poll."):
        super().__init__(message)
