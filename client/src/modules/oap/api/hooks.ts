/** Data access for the OAP module. Every write invalidates the whole module's
 *  cache: a stale queue is the defect this module is most likely to ship. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  Bonafide, Claim, Leave, LeaveInput, NoDuesCase, Notice, Page,
  SeminarRequest, SeminarSchedule, TAAssignment, ThesisAssignment,
} from "./types";

export const KEY = "oap";

export const keys = {
  leave: () => [KEY, "leave"] as const,
  bonafide: () => [KEY, "bonafide"] as const,
  noDues: () => [KEY, "no-dues"] as const,
  claims: () => [KEY, "claims"] as const,
  thesis: () => [KEY, "thesis"] as const,
  ta: () => [KEY, "ta"] as const,
  seminars: () => [KEY, "seminars"] as const,
  schedules: () => [KEY, "schedules"] as const,
  notices: () => [KEY, "notices"] as const,
};

/** The list endpoints are cursor-paged; the no-dues list is a plain array. */
export function unwrap<T>(data: Page<T> | T[]): T[] {
  return Array.isArray(data) ? data : data.results;
}

function useList<T>(key: readonly unknown[], path: string) {
  return useQuery({
    queryKey: key,
    queryFn: async () => unwrap((await http.get<Page<T> | T[]>(path)).data),
    staleTime: 15_000,
  });
}

function useCommand<V, R>(run: (vars: V) => Promise<R>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (vars: V) => {
      const result = await run(vars);
      qc.invalidateQueries({ queryKey: [KEY] });
      return result;
    },
  });
}

const body = <T,>(r: { data: T }) => r.data;

// -- leave ---------------------------------------------------------------------
export const useLeaves = () =>
  useList<Leave>(keys.leave(), "/oap/leave-applications");

export const useSubmitLeave = () =>
  useCommand((b: LeaveInput) =>
    http.post<Leave>("/oap/leave-applications", b).then(body));

export const useLeaveDecision = () =>
  useCommand(({ id, outcome }: { id: number; outcome: "approve" | "reject" }) =>
    http.post<Leave>(`/oap/leave-applications/${id}/decision`, { outcome }).then(body));

// -- bonafide ------------------------------------------------------------------
export const useBonafides = () =>
  useList<Bonafide>(keys.bonafide(), "/oap/bonafide-requests");

export const useRequestBonafide = () =>
  useCommand((purpose: string) =>
    http.post<Bonafide>("/oap/bonafide-requests", { purpose }).then(body));

export const useVerifyBonafide = () =>
  useCommand((id: number) =>
    http.post<Bonafide>(`/oap/bonafide-requests/${id}/verify`).then(body));

export const useBonafideDecision = () =>
  useCommand(({ id, outcome }: { id: number; outcome: "approve" | "reject" }) =>
    http.post<Bonafide>(`/oap/bonafide-requests/${id}/decision`, { outcome }).then(body));

// -- no-dues -------------------------------------------------------------------
export const useNoDues = () =>
  useList<NoDuesCase>(keys.noDues(), "/oap/no-dues-cases");

export const useInitiateNoDues = () =>
  useCommand(() => http.post("/oap/no-dues-cases").then(body));

export const useRecordNoDuesResult = () =>
  useCommand(({ id, result }: { id: number; result: "clear" | "outstanding" }) =>
    http.post(`/oap/no-dues-cases/${id}/results`, { result }).then(body));

export const useFinalizeNoDues = () =>
  useCommand((id: number) =>
    http.post(`/oap/no-dues-cases/${id}/finalize`).then(body));

// -- assistantship -------------------------------------------------------------
export const useClaims = () =>
  useList<Claim>(keys.claims(), "/oap/assistantship-claims");

export const useSubmitClaim = () =>
  useCommand(() => http.post<Claim>("/oap/assistantship-claims").then(body));

export const useVerifyClaim = () =>
  useCommand(({ id, role }: { id: number; role: "thesis" | "ta" }) =>
    http.post<Claim>(`/oap/assistantship-claims/${id}/verifications`, { role }).then(body));

export const useForwardClaim = () =>
  useCommand((id: number) =>
    http.post<Claim>(`/oap/assistantship-claims/${id}/forward`).then(body));

export const useClaimDecision = () =>
  useCommand(({ id, outcome }: { id: number; outcome: "approve" | "reject" }) =>
    http.post<Claim>(`/oap/assistantship-claims/${id}/decision`, { outcome }).then(body));

export const useProcessStipend = () =>
  useCommand((id: number) =>
    http.post<Claim>(`/oap/assistantship-claims/${id}/stipend`).then(body));

// -- assignments ---------------------------------------------------------------
export const useThesisAssignments = () =>
  useList<ThesisAssignment>(keys.thesis(), "/oap/thesis-supervisor-assignments");

export const useTAAssignments = () =>
  useList<TAAssignment>(keys.ta(), "/oap/ta-assignments");

export const useRecordThesis = () =>
  useCommand((b: { student_user_id: number; supervisor_user_id: number }) =>
    http.post<ThesisAssignment>("/oap/thesis-supervisor-assignments", b).then(body));

export const useRecordTA = () =>
  useCommand((b: { student_user_id: number; course_code: string;
                   supervisor_user_id: number | null }) =>
    http.post<TAAssignment>("/oap/ta-assignments", b).then(body));

// -- seminars ------------------------------------------------------------------
export const useSeminarRequests = () =>
  useList<SeminarRequest>(keys.seminars(), "/oap/seminar-requests");

export const useRequestSeminar = () =>
  useCommand(() => http.post<SeminarRequest>("/oap/seminar-requests").then(body));

export const useScheduleSeminar = () =>
  useCommand(({ id, scheduled_for, venue }:
    { id: number; scheduled_for: string; venue: string }) =>
    http.post<SeminarSchedule>(`/oap/seminar-requests/${id}/schedule`,
      { scheduled_for, venue }).then(body));

export const useSeminarSchedules = () =>
  useList<SeminarSchedule>(keys.schedules(), "/oap/seminar-schedules");

// -- notifications -------------------------------------------------------------
export const useNotices = () =>
  useList<Notice>(keys.notices(), "/oap/notifications");
