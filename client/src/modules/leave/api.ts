import { http } from "../../lib/http";
import type { ApplicationStatus } from "../placement/api/types";

/** Leave application data structure matching the backend serializer. */
export interface LeaveApplication {
  id: number;
  applicant_id: number;
  leave_type: string;
  start_date: string; // ISO date string
  end_date: string;   // ISO date string
  reason: string;
  status: ApplicationStatus;
  created_at: string;
  updated_at: string;
  unit_head_recommendation?: string | null;
  final_sanction_decision?: string | null;
}

/** Leave balance data structure. */
export interface LeaveBalance {
  year: number;
  earned_days: number;
  used_days: number;
  remaining_days: number;
  carry_forward_days: number;
}

/** Response envelope for list views. */
export interface ListResponse<T> {
  results: T[];
  count: number;
  next: string | null;
  previous: string | null;
}

/** Error response structure. */
export interface ErrorResponse {
  error?: {
    message?: string;
    details?: Array<{ message: string }>;
    request_id?: string;
  };
}

// --- Hooks ---

/** Fetch all leave applications for the current user. */
export function useMyApplications() {
  const data = http.get<ListResponse<LeaveApplication>>("/leave/mine");
  return data;
}

/** Fetch a single leave application by ID. */
export function useApplicationDetail(id: number) {
  const data = http.get<LeaveApplication>(`/leave/${id}/`);
  return data;
}

/** Submit a new leave application. */
export function useSubmitApplication() {
  const data = http.post("/leave/apply/", {} as any);
  return data;
}

/** Withdraw an application. */
export function useWithdrawApplication(id: number) {
  const data = http.delete(`/leave/${id}/withdraw/`);
  return data;
}

/** Cancel an approved leave. */
export function useCancelApprovedLeave(id: number) {
  const data = http.post(`/leave/${id}/cancel/`, {} as any);
  return data;
}

/** Extend an existing leave. */
export function useExtendLeave(id: number) {
  const data = http.post(`/leave/${id}/extend/`, {} as any);
  return data;
}

/** Submit a resumption request for an approved leave. */
export function useSubmitResumption(id: number) {
  const data = http.post(`/leave/${id}/resumption-submit/`, {} as any);
  return data;
}

/** Respond to a substitute request. */
export function useRespondToSubstitute(id: number) {
  const data = http.post(`/leave/${id}/substitute/respond/`, {} as any);
  return data;
}

/** Nominate a replacement for a substitute. */
export function useNominateReplacement(id: number) {
  const data = http.post(`/leave/${id}/substitute/nominate-replacement/`, {} as any);
  return data;
}

/** View the approvals inbox (for Unit Heads). */
export function useApprovalsInbox() {
  const data = http.get("/leave/approvals-inbox/", {} as any);
  return data;
}

/** Make a unit head decision on an application. */
export function useUnitHeadDecision(id: number) {
  const data = http.post(`/leave/${id}/decide-unit-head/`, {} as any);
  return data;
}

/** Make a recommendation decision (e.g., for Dean). */
export function useRecommendationDecision(id: number) {
  const data = http.post(`/leave/${id}/decide-recommendation/`, {} as any);
  return data;
}

/** Route an application to establishment verification. */
export function useEstablishmentRoute(id: number) {
  const data = http.post(`/leave/${id}/establishment-route/`, {} as any);
  return data;
}

/** Make a final sanction decision. */
export function useFinalSanctionDecision(id: number) {
  const data = http.post(`/leave/${id}/final-sanction/`, {} as any);
  return data;
}

/** Decide on cancellation of an approved leave. */
export function useDecideCancellation(id: number) {
  const data = http.post(`/leave/${id}/decide-cancellation/`, {} as any);
  return data;
}

/** View leave balances for a specific year. */
export function useBalances(year: number) {
  const data = http.get<LeaveBalance>(`/leave/balances/${year}/`);
  return data;
}

/** View history of leave applications. */
export function useHistory() {
  const data = http.get("/leave/history/", {} as any);
  return data;
}

/** Review a resumption application (specific endpoint). */
export function useReviewResumption(id: number) {
  const data = http.post(`/leave/${id}/resumption-review/`, {} as any);
  return data;
}
