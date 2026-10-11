from dataclasses import dataclass

@dataclass(frozen=True)
class LeaveRequestState:
    status: str

class LeaveRequestStateMachine:
    def __init__(self, initial_state: LeaveRequestState):
        self.state = initial_state

    def apply_transition(self, transition: str):
        if transition == 'approve':
            self.state = LeaveRequestState(status='approved')
        elif transition == 'reject':
            self.state = LeaveRequestState(status='rejected')
        elif transition == 'cancel':
            self.state = LeaveRequestState(status='cancelled')
