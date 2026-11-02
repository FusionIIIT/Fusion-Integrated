export interface BookingRequestData {
    indenter: string;
    visitor_name: string;
    visitor_email: string;
    visitor_phone: string;
    visitor_category: 'A' | 'B' | 'C' | 'D';
    booking_from: string;
    booking_to: string;
    billing_responsibility: 'Visitor' | 'Indenter' | 'Institute' | 'Project';
    purpose: string;
    is_offline?: boolean;
}

export async function submitBooking(data: BookingRequestData) {
    const res = await fetch('/api/v1/vh/bookings/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    return res.json();
}

export async function fetchMyBookings() {
    const res = await fetch('/api/v1/vh/bookings/');
    return res.json();
}

export async function fetchAvailableRooms() {
    const res = await fetch('/api/v1/vh/rooms/available/');
    return res.json();
}

export async function forwardBooking(bookingId: string) {
    const res = await fetch(`/api/v1/vh/bookings/${bookingId}/forward/`, { method: 'POST' });
    return res.json();
}

export async function rejectBooking(bookingId: string, reason: string) {
    const res = await fetch(`/api/v1/vh/bookings/${bookingId}/reject/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason })
    });
    return res.json();
}

export async function approveBooking(bookingId: string) {
    const res = await fetch(`/api/v1/vh/bookings/${bookingId}/approve/`, { method: 'POST' });
    return res.json();
}

export async function allotRoom(bookingId: string, roomNumber: string) {
    const res = await fetch('/api/v1/vh/stays/allot/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ booking_id: bookingId, room_number: roomNumber })
    });
    return res.json();
}

export async function settleBill(billNumber: string, amount: string) {
    const res = await fetch(`/api/v1/vh/bills/${billNumber}/settle/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ amount })
    });
    return res.json();
}


