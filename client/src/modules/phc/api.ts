import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../lib/http";

const KEY = "phc";
export interface Patient { id: number; user_id: number; patient_number: string; created_at: string }
export interface Doctor { id: number; user_id: number; specialty: string; is_available: boolean }
export interface Appointment {
  id: number; patient: number; doctor: number; starts_at: string;
  status: string; reason: string; created_at: string;
}
export interface Medicine {
  id: number; name: string; unit: string; quantity: number;
  low_stock_threshold: number; expires_on: string | null; is_active: boolean;
}
export interface Announcement { id: number; title: string; body: string; created_at: string }
export interface InventoryTransaction { id: number; medicine: number; medicine_name: string;
  transaction_type: string; quantity: number; actor_user_id: number; patient_id: number | null;
  note: string; created_at: string }
export interface Page<T> { results: T[]; next: string | null; previous: string | null }

const invalidate = (qc: ReturnType<typeof useQueryClient>) =>
  qc.invalidateQueries({ queryKey: [KEY] });

export const usePatients = (q = "") => useQuery({ queryKey: [KEY, "patients", q],
  queryFn: async () => (await http.get<Page<Patient>>("/phc/patients", { params: q ? { q } : {} })).data });
export const useDoctors = () => useQuery({ queryKey: [KEY, "doctors"],
  queryFn: async () => (await http.get<Page<Doctor>>("/phc/doctors")).data });
export const useAppointments = () => useQuery({ queryKey: [KEY, "appointments"],
  queryFn: async () => (await http.get<Page<Appointment>>("/phc/appointments")).data });
export const useMedicines = () => useQuery({ queryKey: [KEY, "medicines"],
  queryFn: async () => (await http.get<Page<Medicine>>("/phc/medicines")).data });
export const useAnnouncements = () => useQuery({ queryKey: [KEY, "announcements"],
  queryFn: async () => (await http.get<Page<Announcement>>("/phc/announcements")).data });
export const useInventoryTransactions = () => useQuery({ queryKey: [KEY, "transactions"],
  queryFn: async () => (await http.get<Page<InventoryTransaction>>("/phc/inventory/transactions")).data });

export function usePhcPost<T>(path: string) {
  const qc = useQueryClient();
  return useMutation({ mutationFn: async (body: unknown) =>
    (await http.post<T>(path, body)).data, onSuccess: () => invalidate(qc) });
}
