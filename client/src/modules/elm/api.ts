import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { http } from "../../lib/http";

export interface LeaveRequest {
  id: number; user_id: number; category: string; kind: string; start_date: string;
  end_date: string; half: string; days: string; purpose: string; status: string;
  current_role: string; substitute_user_id: number | null; substitute_status: string;
  station_leave: boolean; recommendation: string; actual_return_date: string | null;
  resumption_kind: string; created_at: string;
  history?: { from: string; to: string; event: string; actor_user_id: number | null; actor_role: string; note: string; at: string }[];
}
export interface LeaveBalance { category: string; year: number; balance: string }
const root = "/elm";
export function useMyLeave() { return useQuery({ queryKey: ["elm", "requests"], queryFn: async () => (await http.get<LeaveRequest[]>(`${root}/requests`)).data }); }
export function useLeaveQueue() { return useQuery({ queryKey: ["elm", "queue"], queryFn: async () => (await http.get<LeaveRequest[]>(`${root}/queue`)).data }); }
export function useLeaveBalances(year?: number) { return useQuery({ queryKey: ["elm", "balances", year], queryFn: async () => (await http.get<LeaveBalance[]>(`${root}/balances`, { params: year ? { year } : {} })).data }); }
function useElmAction<TInput>(key: string, action: (input: TInput) => Promise<unknown>) {
  const qc = useQueryClient();
  return useMutation({ mutationKey: ["elm", key], mutationFn: action, onSuccess: async () => { await Promise.all([qc.invalidateQueries({ queryKey: ["elm"] })]); } });
}
export function useCreateLeave() { return useElmAction("create", async (data: Record<string, unknown>) => (await http.post(`${root}/requests`, data)).data); }
export function useLeaveAction() { return useElmAction("action", async (data: { id: number; action: "withdraw" | "cancel" | "resume" | "extend"; payload?: Record<string, unknown> }) => (await http.post(`${root}/requests/${data.id}/${data.action}`, data.payload ?? {})).data); }
export function useDecideLeave() { return useElmAction("decide", async (data: { id: number; decision: string; note: string }) => (await http.post(`${root}/queue/${data.id}/decide`, { decision: data.decision, note: data.note })).data); }
export function usePolicy() { return useQuery({ queryKey: ["elm", "policy"], queryFn: async () => (await http.get<{ params: Record<string, unknown>; hierarchy: Record<string, unknown> }>(`${root}/admin/policies`)).data }); }
export function useSavePolicy() { return useElmAction("save-policy", async (data: { params: Record<string, unknown>; hierarchy: Record<string, unknown> }) => (await http.post(`${root}/admin/policies`, data)).data); }

export function useSubstitutions() { return useQuery({ queryKey: ["elm", "substitutions"], queryFn: async () => (await http.get<LeaveRequest[]>(`${root}/substitutions`)).data }); }
export function useSubstituteResponse() { return useElmAction("substitute-response", async (data: { id: number; accept: boolean; note?: string }) => (await http.post(`${root}/substitutions/${data.id}/respond`, { accept: data.accept, note: data.note ?? "" })).data); }

export interface CalendarEntry { kind: string; start_date: string; end_date: string; label?: string }
export interface CalendarVersion { id: number; name: string; status: string; effective_from: string; entries: CalendarEntry[] }
export function useCalendars() { return useQuery({ queryKey: ["elm", "calendars"], queryFn: async () => (await http.get<CalendarVersion[]>(`${root}/admin/calendars`)).data }); }
export function useCreateCalendar() { return useElmAction("create-calendar", async (data: { name: string; effective_from: string; entries: CalendarEntry[] }) => (await http.post(`${root}/admin/calendars`, data)).data); }
export function usePublishCalendar() { return useElmAction("publish-calendar", async (id: number) => (await http.post(`${root}/admin/calendars/${id}/publish`)).data); }
export function useCreateOfflineRecord() { return useElmAction("offline-record", async (data: Record<string, unknown>) => (await http.post(`${root}/admin/offline`, data)).data); }

export interface SlaConfig { reminder_hours: number | null; escalation_hours: number | null; escalation_role: string }
export function useSlaConfig() { return useQuery({ queryKey: ["elm", "sla"], queryFn: async () => (await http.get<SlaConfig>(`${root}/admin/sla`)).data }); }
export function useSaveSlaConfig() { return useElmAction("save-sla", async (data: SlaConfig) => (await http.post(`${root}/admin/sla`, data)).data); }
export interface OfflineRecord {
  id: number; user_id: number; category: string; start_date: string; end_date: string;
  days: string; sanction_reference: string; evidence: unknown[]; note: string;
  synced_request_id: number | null;
}
export function useOfflineRecords() { return useQuery({ queryKey: ["elm", "offline-records"], queryFn: async () => (await http.get<OfflineRecord[]>(`${root}/admin/offline`)).data }); }
export function useMaintainOfflineRecord() { return useElmAction("maintain-offline-record", async (data: { id: number; sanction_reference?: string; evidence?: unknown[]; note?: string }) => (await http.patch(`${root}/admin/offline/${data.id}`, { sanction_reference: data.sanction_reference, evidence: data.evidence, note: data.note })).data); }
export function useResumptionQueue() { return useQuery({ queryKey: ["elm", "resumptions"], queryFn: async () => (await http.get<LeaveRequest[]>(`${root}/resumptions`)).data }); }
export function useVerifyResumption() { return useElmAction("verify-resumption", async (data: { id: number; note: string }) => (await http.post(`${root}/resumptions/${data.id}/verify`, { note: data.note })).data); }

export function useReplacementSubstitute() { return useElmAction("replacement-substitute", async (data: { id: number; substitute_user_id: number }) => (await http.post(`${root}/requests/${data.id}/substitute`, { substitute_user_id: data.substitute_user_id })).data); }
