
from enum import Enum, auto



class LeaveStatus(Enum):

    DRAFT = auto()

    AWAITING_SUBSTITUTE = auto()

    AWAITING_UNIT_HEAD = auto()

    APPROVED = auto()

    REJECTED = auto()



class Transition:

    def __init__(self, from_status, to_status, permission=None, guards=None, effects=None):

        self.from_status = from_status

        self.to_status = to_status

        self.permission = permission

        self.guards = guards or []

        self.effects = effects or []



    def is_valid(self, current_status, permissions):

        if current_status != self.from_status:

            return False

        if self.permission and self.permission not in permissions:

            return False

        for guard in self.guards:

            if not guard(permissions):

                return False

        return True



def is_unit_head(permissions):

    return 'leave_management.unit_head.review' in permissions



def is_substitute(permissions):

    return 'leave_management.substitute.assign' in permissions



TRANSITIONS = [

    Transition(LeaveStatus.DRAFT, LeaveStatus.AWAITING_SUBSTITUTE,
permission='leave_management.request.create'),

    Transition(LeaveStatus.AWAITING_SUBSTITUTE, LeaveStatus.AWAITING_UNIT_HEAD, guards=[is_substitute]),

    Transition(LeaveStatus.AWAITING_UNIT_HEAD, LeaveStatus.APPROVED, guards=[is_unit_head]),

    Transition(LeaveStatus.AWAITING_UNIT_HEAD, LeaveStatus.REJECTED, guards=[is_unit_head]),

    Transition(LeaveStatus.DRAFT, LeaveStatus.REJECTED, permission='leave_management.request.create'),  

]                                                                                                       
                                                                                                        
                                                                                                        
                                                                                                        
def get_valid_transitions(current_status, permissions):
                                                                                                        
    return [t for t in TRANSITIONS if t.is_valid(current_status, permissions)]
                                                                                         