from modules.visitors_hostel.models import Booking


def visible_bookings(actor):
    qs = Booking.objects.all()
    if actor.has_permission("visitor_hostel.booking.view"):
        return qs
    if actor.has_permission("visitor_hostel.booking.view_self"):
        return qs.filter(indenter_user_id=actor.user_id)
    return qs.none()
