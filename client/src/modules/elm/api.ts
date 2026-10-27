import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "../../auth/AuthProvider";
import { http } from "../../lib/http";
import { elmRequestPath } from "./paths";

export interface LeaveApplication {
  id: number; user_id: number; kind: string; parent_id: number | null;
  category: string; start_date: string; end_date: string; effective_end_date: string;
  half: string; reason: string; station_leave: boolean; station_details: string;
  status: string; revision: number; substitute_id: number | null;
  offline_reference: string;
  resumption_reviewed: boolean; days_by_year: Record<string, string>;
  allowed_actions: string[];
  history: { id: number; action: string; reason: string; to_status: string; created_at: string }[];
}
export interface Page<T> { results: T[]; next: string | null; previous: string | null }
export interface Employee { user_id: number; display_name: string; kind: string }
export interface Account { year: number; cl: string; rh: string; scl: string; el: string; col: string; vl: string }
export interface Task { id: number; application_id: number; stage: string; role: string }
export interface Notice { id: number; application_id: number; message: string; read: boolean }
export interface Entry { id: number; year: number; category: string; delta: string; operation: string }
export interface Policy { non_working_weekdays: number[]; require_col_evidence: boolean; reminder_hours: number; escalation_hours: number }
export interface Step { stage: string; user_id: number; role: string; escalation_user_id?: number; escalation_role?: string; reassign_on_escalation?: boolean }
export interface EmployeeConfig { user_id: number; unit: string; designation: string; coverage_required: boolean; eligible_categories: string[]; routes: Record<string, Step[]> }
export interface Configuration { policy: Policy | null; employees: EmployeeConfig[]; calendars: {id: number; year: number; published: boolean}[]; attendance_outbox: {id: number}[] }

export function useElmQuery<T>(path: string, enabled = true) {
  const { session } = useAuth();
  return useQuery({
    queryKey: ["elm", session?.user.id, session?.active_role, path],
    queryFn: async () => (await http.get<T>(elmRequestPath(path))).data,
    enabled: enabled && Boolean(session), retry: false,
  });
}

export function useElmWrite() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async ({path, data, method = "post"}: {path: string; data: unknown; method?: "post" | "put"}) =>
      (await http[method](`/elm/${path}`, data)).data,
    onSuccess: () => client.invalidateQueries({ queryKey: ["elm"] }),
  });
}
