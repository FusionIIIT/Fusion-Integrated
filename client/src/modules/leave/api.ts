import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../lib/http";

/** Leave category types as per DESIGN.md */
export type LeaveCategory = "CL" | "RH" | "SCL" | "EL" | "COL" | "VL";

/** Half day options as per DESIGN.md */
export type HalfDay = "none" | "first" | "second";

/** Stage types as per DESIGN.md */
export type Stage = "substitute" | "unit_head" | "establishment" | "sanction" | "done";

/** Status types as per DESIGN.md */
export type Status = "pending" | "approved" | "rejected" | "withdrawn" | "cancelled";

/** Substitute status types as per DESIGN.md */
export type SubstituteStatus = "not_required" | "pending" | "accepted" | "declined";

/** Decision types for the decide endpoint as per serializers.py */
export type Decision = "approve" | "reject" | "recommended" | "not_recommended" | "verify";

/** Leave action data structure matching LeaveActionSerializer */
export interface LeaveAction {
  id: number;
  actor_id: number;
  action: string;
  remark: string;
  created_at: string;
}

/** Leave application data structure matching LeaveApplicationSerializer.
 * Note: days is a string because DRF sends DecimalField values as strings. */
export interface LeaveApplication {
  id: number;
  user_id: number;
  kind: "leave" | "cancellation";
  parent: number | null;
  category: LeaveCategory;
  start_date: string; // ISO date string
  end_date: string;   // ISO date string
  half_day: HalfDay;
  days: string;       // String representation of Decimal
  purpose: string;
  station_leave: boolean;
  station_address: string;
  substitute_id: number | null;
  substitute_status: SubstituteStatus;
  unit_head_id: number | null;
  establishment_id: number | null;
  sanctioning_authority_id: number | null;
  unit_head_recommendation: string | null;
  stage: Stage;
  status: Status;
  assignee_id: number | null;
  decided_at: string | null;
  created_at: string;
  actions: LeaveAction[];
}

/** Leave balance data structure matching LeaveBalanceSerializer.
 * Note: entitled, used, and available are strings because DRF sends DecimalField values as strings. */
export interface LeaveBalance {
  id: number;
  category: LeaveCategory;
  year: number;
  entitled: string; // String representation of Decimal
  used: string;     // String representation of Decimal
  available: string; // String representation of Decimal (entitled - used)
}

/** Input type for applying a leave as per ApplySerializer */
export interface ApplyInput {
  category: LeaveCategory;
  start_date: string;
  end_date: string;
  half_day: HalfDay;
  purpose: string;
  station_leave: boolean;
  station_address: string;
  substitute_id: number | null;
}

/** Label mapping for leave categories */
export const CATEGORY_LABELS: Record<LeaveCategory, string> = {
  CL: "Casual Leave",
  RH: "Restricted Holiday",
  SCL: "Special Casual Leave",
  EL: "Earned Leave",
  COL: "Commuted Leave",
  VL: "Vacation Leave",
};

/** Helper to normalize list responses from the API. */
function asList<T>(data: T[] | { results: T[] }): T[] {
  return Array.isArray(data) ? data : data.results;
}

// --- Queries ---

/** Fetch all leave applications for the current user. */
export function useMyApplications() {
  return useQuery({
    queryKey: ["leave", "applications"],
    queryFn: async () => asList((await http.get<LeaveApplication[]>("/leave/applications/")).data),
  });
}

/** Fetch a single leave application by ID. */
export function useApplicationDetail(id: number) {
  return useQuery({
    queryKey: ["leave", "application", id],
    queryFn: async () => (await http.get<LeaveApplication>(`/leave/applications/${id}/`)).data,
  });
}

/** Fetch the approvals inbox (for Unit Heads). */
export function useInbox() {
  return useQuery({
    queryKey: ["leave", "inbox"],
    queryFn: async () => asList((await http.get<LeaveApplication[]>("/leave/inbox/")).data),
  });
}

/** Fetch leave balances for a specific year. */
export function useBalances(year: number) {
  return useQuery({
    queryKey: ["leave", "balances", year],
    queryFn: async () => asList((await http.get<LeaveBalance[]>("/leave/balances/", { params: { year } })).data),
  });
}

// --- Mutations ---

/** Submit a new leave application. */
export function useApply() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (vars: ApplyInput) => {
      const response = await http.post("/leave/applications/", vars);
      return response.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["leave"] });
    },
  });
}

/** Withdraw an application. */
export function useWithdraw() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (vars: { id: number }) => {
      const response = await http.post(`/leave/applications/${vars.id}/withdraw/`, {});
      return response.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["leave"] });
    },
  });
}

/** Cancel an approved leave. */
export function useCancel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (vars: { id: number }) => {
      const response = await http.post(`/leave/applications/${vars.id}/cancel/`, {});
      return response.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["leave"] });
    },
  });
}

/** Respond to a substitute request. */
export function useSubstituteResponse() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (vars: { id: number; accept: boolean }) => {
      const response = await http.post(`/leave/applications/${vars.id}/substitute-response/`, vars);
      return response.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["leave"] });
    },
  });
}

/** Nominate a replacement for a substitute. */
export function useReplaceSubstitute() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (vars: { id: number; substitute_id: number }) => {
      const response = await http.post(`/leave/applications/${vars.id}/replace-substitute/`, vars);
      return response.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["leave"] });
    },
  });
}

/** Make a decision on an application (approve/reject/recommend). */
export function useDecide() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (vars: { id: number; decision: Decision; remark: string }) => {
      const response = await http.post(`/leave/applications/${vars.id}/decide/`, vars);
      return response.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["leave"] });
    },
  });
}

/** Who decides a person's leave (ReportingLineSerializer). */
export interface ReportingLine {
  user_id: number;
  unit_head_id: number;
  establishment_id: number | null;
  sanctioning_authority_id: number | null;
}

/** Load one person's reporting line; a 404 means none is configured yet. */
export function useReportingLine(userId: number | null) {
  return useQuery({
    queryKey: ["leave", "reporting-line", userId],
    queryFn: async () => (await http.get<ReportingLine>(`/leave/reporting-lines/${userId}/`)).data,
    enabled: userId !== null,
    retry: false,
  });
}

/** Create or replace a person's reporting line (Leave Administrator only). */
export function useSetReportingLine() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (vars: ReportingLine) =>
      (await http.put<ReportingLine>(`/leave/reporting-lines/${vars.user_id}/`, vars)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["leave"] }),
  });
}
