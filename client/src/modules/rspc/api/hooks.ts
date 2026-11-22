/** TanStack Query hooks for RSPC module data access.
 *
 * All network calls go through lib/http.ts.
 * Mutations invalidate related query keys for automatic cache consistency.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { http } from "../../../lib/http";
import type {
  Project,
  ProjectBudgetHead,
  ProjectFundTransaction,
  Proposal,
} from "./types";

const KEY = "rspc";

export const keys = {
  proposals: (status?: string) => [KEY, "proposals", status] as const,
  proposal: (id: number) => [KEY, "proposal", id] as const,
  projects: (status?: string) => [KEY, "projects", status] as const,
  project: (id: number) => [KEY, "project", id] as const,
  budgetHeads: (projectId: number) => [KEY, "budgetHeads", projectId] as const,
  ledger: (projectId: number) => [KEY, "ledger", projectId] as const,
};

// --- Proposals ---------------------------------------------------------------

export function useProposals(status?: string) {
  return useQuery({
    queryKey: keys.proposals(status),
    queryFn: async () => {
      const res = await http.get<Proposal[]>("/rspc/proposals/", {
        params: status ? { status } : undefined,
      });
      return res.data;
    },
    staleTime: 30_000,
  });
}

export function useProposal(id: number | undefined) {
  return useQuery({
    queryKey: keys.proposal(id!),
    queryFn: async () => {
      const res = await http.get<Proposal>(`/rspc/proposals/${id}/`);
      return res.data;
    },
    enabled: typeof id === "number",
  });
}

export function useCreateProposal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<Proposal>) => {
      const res = await http.post<Proposal>("/rspc/proposals/", payload);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY, "proposals"] });
    },
  });
}

export function useSubmitProposal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const res = await http.post<Proposal>(`/rspc/proposals/${id}/submit/`);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY, "proposals"] });
    },
  });
}

export function useEndorseProposal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, comments }: { id: number; comments: string }) => {
      const res = await http.post<Proposal>(`/rspc/proposals/${id}/endorse/`, { comments });
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY, "proposals"] });
    },
  });
}

export function useApproveProposal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, comments }: { id: number; comments: string }) => {
      const res = await http.post<Proposal>(`/rspc/proposals/${id}/approve/`, { comments });
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY, "proposals"] });
    },
  });
}

// --- Projects ----------------------------------------------------------------

export function useProjects(status?: string) {
  return useQuery({
    queryKey: keys.projects(status),
    queryFn: async () => {
      const res = await http.get<Project[]>("/rspc/projects/", {
        params: status ? { status } : undefined,
      });
      return res.data;
    },
    staleTime: 30_000,
  });
}

export function useProject(id: number | undefined) {
  return useQuery({
    queryKey: keys.project(id!),
    queryFn: async () => {
      const res = await http.get<Project>(`/rspc/projects/${id}/`);
      return res.data;
    },
    enabled: typeof id === "number",
  });
}

export function useActivateProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const res = await http.post<Project>(`/rspc/projects/${id}/activate/`);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY, "projects"] });
    },
  });
}

// --- Finance & Ledger --------------------------------------------------------

export function useBudgetHeads(projectId: number | undefined) {
  return useQuery({
    queryKey: keys.budgetHeads(projectId!),
    queryFn: async () => {
      const res = await http.get<ProjectBudgetHead[]>(`/rspc/projects/${projectId}/heads/`);
      return res.data;
    },
    enabled: typeof projectId === "number",
  });
}

export function useAllocateBudget() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      projectId,
      head_type,
      allocated_amount,
    }: {
      projectId: number;
      head_type: string;
      allocated_amount: string;
    }) => {
      const res = await http.post<ProjectBudgetHead>(`/rspc/projects/${projectId}/heads/`, {
        head_type,
        allocated_amount,
      });
      return res.data;
    },
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: keys.budgetHeads(variables.projectId) });
      qc.invalidateQueries({ queryKey: [KEY, "projects"] });
    },
  });
}

export function useDisburseFund() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      projectId,
      head_type,
      amount,
      reference_no,
      description,
    }: {
      projectId: number;
      head_type: string;
      amount: string;
      reference_no: string;
      description: string;
    }) => {
      const res = await http.post<ProjectFundTransaction>(
        `/rspc/projects/${projectId}/disburse/`,
        { head_type, amount, reference_no, description }
      );
      return res.data;
    },
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: keys.ledger(variables.projectId) });
      qc.invalidateQueries({ queryKey: keys.budgetHeads(variables.projectId) });
    },
  });
}

export function useLedger(projectId: number | undefined) {
  return useQuery({
    queryKey: keys.ledger(projectId!),
    queryFn: async () => {
      const res = await http.get<ProjectFundTransaction[]>(
        `/rspc/projects/${projectId}/ledger/`
      );
      return res.data;
    },
    enabled: typeof projectId === "number",
  });
}
