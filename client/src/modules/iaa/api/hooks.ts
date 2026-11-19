/** Data access hooks for Institute Accounts and Audits (IAA) module. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { http } from "../../../lib/http";
import type {
  ExpenseRequest,
  TravelAllowanceClaim,
  DepartmentBudget,
  AnomalyRecord,
  AuditObservation,
  ApprovalAction,
} from "./types";

const KEY = "iaa";

export const keys = {
  all: [KEY] as const,
  expenses: () => [KEY, "expenses"] as const,
  expense: (id: number) => [KEY, "expense", id] as const,
  taClaims: () => [KEY, "ta-claims"] as const,
  taClaim: (id: number) => [KEY, "ta-claim", id] as const,
  budgets: () => [KEY, "budgets"] as const,
  anomalies: () => [KEY, "anomalies"] as const,
  auditObservations: () => [KEY, "audit-observations"] as const,
  actions: () => [KEY, "actions"] as const,
};

function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: [KEY] });
}

// -- Expense Requests ---------------------------------------------------------
export function useExpenses() {
  return useQuery({
    queryKey: keys.expenses(),
    queryFn: async () => {
      const res = await http.get<ExpenseRequest[] | { results: ExpenseRequest[] }>("/iaa/expenses/");
      return Array.isArray(res.data) ? res.data : res.data.results || [];
    },
    staleTime: 15_000,
  });
}

export function useCreateExpense() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { title: string; description: string; department: string; amount: string; creator_user_id?: string; creator_role?: string }) => {
      return (await http.post<ExpenseRequest>("/iaa/expenses/", payload)).data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useSubmitExpense() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      return (await http.post<ExpenseRequest>(`/iaa/expenses/${id}/submit/`, {})).data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useApproveExpense() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, actor_user_id, actor_role, remarks }: { id: number; actor_user_id?: string; actor_role?: string; remarks: string }) => {
      return (await http.post<ExpenseRequest>(`/iaa/expenses/${id}/approve/`, { action: "approve", actor_user_id, actor_role, remarks })).data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useRejectExpense() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, actor_user_id, actor_role, remarks }: { id: number; actor_user_id?: string; actor_role?: string; remarks: string }) => {
      return (await http.post<ExpenseRequest>(`/iaa/expenses/${id}/reject/`, { action: "reject", actor_user_id, actor_role, remarks })).data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useCompleteExpense() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      return (await http.post<ExpenseRequest>(`/iaa/expenses/${id}/mark_completed/`, {})).data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Travel Allowance Claims --------------------------------------------------
export function useTAClaims() {
  return useQuery({
    queryKey: keys.taClaims(),
    queryFn: async () => {
      const res = await http.get<TravelAllowanceClaim[] | { results: TravelAllowanceClaim[] }>("/iaa/ta-claims/");
      return Array.isArray(res.data) ? res.data : res.data.results || [];
    },
    staleTime: 15_000,
  });
}

export function useCreateTAClaim() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      claimant_user_id?: string;
      claimant_role?: string;
      purpose: string;
      travel_start_date: string;
      travel_end_date: string;
      departure_location: string;
      destination_location: string;
      total_amount: string;
    }) => {
      return (await http.post<TravelAllowanceClaim>("/iaa/ta-claims/", payload)).data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useApproveTAClaim() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, remarks }: { id: number; remarks: string }) => {
      return (await http.post<TravelAllowanceClaim>(`/iaa/ta-claims/${id}/approve/`, { action: "approve", remarks })).data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Budgets -------------------------------------------------------------------
export function useBudgets() {
  return useQuery({
    queryKey: keys.budgets(),
    queryFn: async () => {
      const res = await http.get<DepartmentBudget[] | { results: DepartmentBudget[] }>("/iaa/budgets/");
      return Array.isArray(res.data) ? res.data : res.data.results || [];
    },
    staleTime: 30_000,
  });
}

// -- Anomalies -----------------------------------------------------------------
export function useAnomalies() {
  return useQuery({
    queryKey: keys.anomalies(),
    queryFn: async () => {
      const res = await http.get<AnomalyRecord[] | { results: AnomalyRecord[] }>("/iaa/anomalies/");
      return Array.isArray(res.data) ? res.data : res.data.results || [];
    },
    staleTime: 15_000,
  });
}

export function useResolveAnomaly() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, resolution, remarks }: { id: number; resolution: "resolve" | "escalate"; remarks: string }) => {
      return (await http.post<AnomalyRecord>(`/iaa/anomalies/${id}/resolve/`, { resolution, remarks })).data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Audit Observations --------------------------------------------------------
export function useAuditObservations() {
  return useQuery({
    queryKey: keys.auditObservations(),
    queryFn: async () => {
      const res = await http.get<AuditObservation[] | { results: AuditObservation[] }>("/iaa/audit-observations/");
      return Array.isArray(res.data) ? res.data : res.data.results || [];
    },
    staleTime: 15_000,
  });
}

export function useCreateAuditObservation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { observation_title: string; observation_details: string; department: string; auditor_user_id?: string }) => {
      return (await http.post<AuditObservation>("/iaa/audit-observations/", payload)).data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useRespondAuditObservation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, department_response }: { id: number; department_response: string }) => {
      return (await http.post<AuditObservation>(`/iaa/audit-observations/${id}/respond/`, { department_response })).data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useCloseAuditObservation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, closure_remarks }: { id: number; closure_remarks: string }) => {
      return (await http.post<AuditObservation>(`/iaa/audit-observations/${id}/close/`, { closure_remarks })).data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Approval Actions Audit Log ------------------------------------------------
export function useApprovalActions() {
  return useQuery({
    queryKey: keys.actions(),
    queryFn: async () => {
      const res = await http.get<ApprovalAction[] | { results: ApprovalAction[] }>("/iaa/actions/");
      return Array.isArray(res.data) ? res.data : res.data.results || [];
    },
    staleTime: 15_000,
  });
}
