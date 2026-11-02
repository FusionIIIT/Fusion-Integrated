from dataclasses import dataclass
from typing import List, Optional

@dataclass(frozen=True)
class BookingSummaryDTO:
    booking_id: str
    indenter: str
    visitor_name: str
    booking_from: str
    booking_to: str
    category: str
    status: str
    billing_responsibility: str

@dataclass(frozen=True)
class ClearanceDTO:
    user_id: str
    is_cleared: bool
    unsettled_bills_count: int
    message: str

def get_active_bookings_for_user(user_id: str) -> List[BookingSummaryDTO]:
    from modules.visitor_hostel.models import BookingDetail
    bookings = BookingDetail.objects.filter(indenter=user_id, status__in=['PENDING', 'FORWARDED', 'APPROVED', 'ROOM_ALLOTTED', 'CHECKED_IN'])
    return [BookingSummaryDTO(b.booking_id, b.indenter, b.visitor.name, str(b.booking_from), str(b.booking_to), b.category, b.status, b.billing_responsibility) for b in bookings]

def get_user_vh_clearance(user_id: str) -> ClearanceDTO:
    from modules.visitor_hostel.models import Bill
    unsettled = Bill.objects.filter(booking__indenter=user_id, settlement_status='Pending').count()
    return ClearanceDTO(user_id=user_id, is_cleared=(unsettled == 0), unsettled_bills_count=unsettled, message="Cleared" if unsettled == 0 else f"{unsettled} unsettled bills pending")
