import { http } from "../../lib/http";

export interface Booking {
  id: number;
  booking_number: string;
  source: "online" | "offline";
  status: string;
  visitor_name: string;
  visitor_category: "A" | "B" | "C" | "D";
  arrival_date: string;
  departure_date: string;
  room_count: number;
  billing_responsibility: string;
}

export interface InventoryItem {
  id: number;
  name: string;
  current_quantity: string;
  minimum_threshold: string;
  unit: string;
}

const base = "/visitors-hostel";

export async function listBookings(): Promise<Booking[]> {
  const { data } = await http.get(`${base}/bookings`);
  return data;
}

export async function createBooking(payload: Record<string, unknown>): Promise<Booking> {
  const { data } = await http.post(`${base}/bookings`, payload);
  return data;
}

export async function createOfflineBooking(payload: Record<string, unknown>): Promise<Booking> {
  const { data } = await http.post(`${base}/bookings/offline`, payload);
  return data;
}

export async function bookingAction(id: number, action: string,
                                    payload: Record<string, unknown> = {}) {
  const { data } = await http.post(`${base}/bookings/${id}/${action}`, payload);
  return data as Booking;
}

export async function listInventory(): Promise<InventoryItem[]> {
  const { data } = await http.get(`${base}/inventory`);
  return data;
}

export async function changeInventory(id: number, delta: number, note: string) {
  const { data } = await http.post(`${base}/inventory/${id}/changes`, { delta, note });
  return data as InventoryItem;
}

export async function getReport(type: string) {
  const { data } = await http.get(`${base}/reports`, { params: { type } });
  return data as Record<string, unknown>;
}
