/** Data access hooks for Other Academic Procedures.
 * Uses the shared lib/http client and TanStack query for caching and invalidation.
 */
import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  BonafideRequest,
  BranchChangeRequest,
  NoDuesDepartmentalSignoff,
  NoDuesRequest,
  Page,
  StudentLeaveRequest,
} from "./types";

const KEY = "oap";

export const keys = {
  all: [KEY] as const,
  leaves: () => [KEY, "leaves"] as const,
  leave: (id: number) => [KEY, "leave", id] as const,
  bonafides: () => [KEY, "bonafides"] as const,
  bonafide: (id: number) => [KEY, "bonafide", id] as const,
  noDues: () => [KEY, "no-dues"] as const,
  noDuesDetail: (id: number) => [KEY, "no-dues", id] as const,
  branchChanges: () => [KEY, "branch-changes"] as const,
  branchChange: (id: number) => [KEY, "branch-change", id] as const,
};

function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: [KEY] });
}

// -- Student Leave Hooks ------------------------------------------------------
export function useLeaves() {
  return useQuery({
    queryKey: keys.leaves(),
    queryFn: async () => {
      const res = await http.get<Page<StudentLeaveRequest> | StudentLeaveRequest[]>("/oap/leave/");
      const data = res.data;
      if (Array.isArray(data)) {
        return { results: data, next: null, previous: null };
      }
      return data;
    },
    staleTime: 30_000,
  });
}

export function useSubmitLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      student_id: string;
      student_name: string;
      leave_type: string;
      start_date: string;
      end_date: string;
      reason: string;
      document_url?: string;
    }) => {
      const res = await http.post<StudentLeaveRequest>("/oap/leave/", payload);
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useRecommendLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, supervisor_id, remarks }: { id: number; supervisor_id?: string; remarks?: string }) => {
      const res = await http.post<StudentLeaveRequest>(`/oap/leave/${id}/recommend/`, {
        supervisor_id,
        remarks,
      });
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useApproveLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, hod_id, remarks }: { id: number; hod_id?: string; remarks?: string }) => {
      const res = await http.post<StudentLeaveRequest>(`/oap/leave/${id}/hod_approve/`, {
        hod_id,
        remarks,
      });
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useRejectLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, hod_id, remarks }: { id: number; hod_id?: string; remarks?: string }) => {
      const res = await http.post<StudentLeaveRequest>(`/oap/leave/${id}/hod_reject/`, {
        hod_id,
        remarks,
      });
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useCancelLeave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, student_id }: { id: number; student_id: string }) => {
      const res = await http.post<StudentLeaveRequest>(`/oap/leave/${id}/cancel/`, { student_id });
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Bonafide Certificate Hooks -----------------------------------------------
export function useBonafides() {
  return useQuery({
    queryKey: keys.bonafides(),
    queryFn: async () => {
      const res = await http.get<Page<BonafideRequest> | BonafideRequest[]>("/oap/bonafide/");
      const data = res.data;
      if (Array.isArray(data)) {
        return { results: data, next: null, previous: null };
      }
      return data;
    },
    staleTime: 30_000,
  });
}

export function useSubmitBonafide() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { student_id: string; purpose: string; details?: string }) => {
      const res = await http.post<BonafideRequest>("/oap/bonafide/", payload);
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useApproveBonafide() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, issued_by, remarks }: { id: number; issued_by?: string; remarks?: string }) => {
      const res = await http.post<{ status: string; certificate_number: string }>(
        `/oap/bonafide/${id}/approve_and_issue/`,
        { issued_by, remarks }
      );
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useRejectBonafide() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, issued_by, reason }: { id: number; issued_by?: string; reason?: string }) => {
      const res = await http.post<BonafideRequest>(`/oap/bonafide/${id}/reject/`, {
        issued_by,
        reason,
      });
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

// -- No-Dues Clearance Hooks --------------------------------------------------
export function useNoDues() {
  return useQuery({
    queryKey: keys.noDues(),
    queryFn: async () => {
      const res = await http.get<Page<NoDuesRequest> | NoDuesRequest[]>("/oap/no-dues/");
      const data = res.data;
      if (Array.isArray(data)) {
        return { results: data, next: null, previous: null };
      }
      return data;
    },
    staleTime: 30_000,
  });
}

export function useInitiateNoDues() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { student_id: string; reason?: string }) => {
      const res = await http.post<NoDuesRequest>("/oap/no-dues/", payload);
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useRecordSignoff() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      department,
      status,
      signoff_by,
      dues_amount,
      remarks,
    }: {
      id: number;
      department: string;
      status: string;
      signoff_by?: string;
      dues_amount?: string;
      remarks?: string;
    }) => {
      const res = await http.post<NoDuesDepartmentalSignoff>(
        `/oap/no-dues/${id}/department_signoff/`,
        { department, status, signoff_by, dues_amount, remarks }
      );
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useFinalizeNoDues() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, finalized_by }: { id: number; finalized_by?: string }) => {
      const res = await http.post<{ cleared: boolean; overall_status: string }>(
        `/oap/no-dues/${id}/finalize/`,
        { finalized_by }
      );
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Branch Change Hooks ------------------------------------------------------
export function useBranchChanges() {
  return useQuery({
    queryKey: keys.branchChanges(),
    queryFn: async () => {
      const res = await http.get<Page<BranchChangeRequest> | BranchChangeRequest[]>(
        "/oap/branch-change/"
      );
      const data = res.data;
      if (Array.isArray(data)) {
        return { results: data, next: null, previous: null };
      }
      return data;
    },
    staleTime: 30_000,
  });
}

export function useSubmitBranchChange() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      student_id: string;
      current_branch: string;
      preferred_branch_1: string;
      preferred_branch_2?: string;
      current_cpi: string;
      credits_completed: number;
      has_backlogs?: boolean;
    }) => {
      const res = await http.post<BranchChangeRequest>("/oap/branch-change/", payload);
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useVerifyBranchChange() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id }: { id: number }) => {
      const res = await http.post<{ eligible: boolean; status: string }>(
        `/oap/branch-change/${id}/verify/`
      );
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useAllocateBranchChange() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      allocated_branch,
      approved_by,
    }: {
      id: number;
      allocated_branch: string;
      approved_by?: string;
    }) => {
      const res = await http.post<BranchChangeRequest>(
        `/oap/branch-change/${id}/allocate/`,
        { allocated_branch, approved_by }
      );
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}
