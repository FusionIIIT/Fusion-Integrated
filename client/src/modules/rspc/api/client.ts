import { http } from "../../../lib/http";
import type { Proposal, Project, ProjectFundTransaction, ProjectBudgetHead } from "./types";

export const rspcApi = {
  getProposals: (status?: string) =>
    http.get<Proposal[]>("/api/v1/rspc/proposals/", { params: status ? { status } : undefined }),

  getProposal: (id: number) =>
    http.get<Proposal>(`/api/v1/rspc/proposals/${id}/`),

  createProposal: (data: Partial<Proposal>) =>
    http.post<Proposal>("/api/v1/rspc/proposals/", data),

  submitProposal: (id: number) =>
    http.post<Proposal>(`/api/v1/rspc/proposals/${id}/submit/`),

  endorseProposal: (id: number, comments: string) =>
    http.post<Proposal>(`/api/v1/rspc/proposals/${id}/endorse/`, { comments }),

  approveProposal: (id: number, comments: string) =>
    http.post<Proposal>(`/api/v1/rspc/proposals/${id}/approve/`, { comments }),

  getProjects: (status?: string) =>
    http.get<Project[]>("/api/v1/rspc/projects/", { params: status ? { status } : undefined }),

  getProject: (id: number) =>
    http.get<Project>(`/api/v1/rspc/projects/${id}/`),

  activateProject: (id: number) =>
    http.post<Project>(`/api/v1/rspc/projects/${id}/activate/`),

  getBudgetHeads: (projectId: number) =>
    http.get<ProjectBudgetHead[]>(`/api/v1/rspc/projects/${projectId}/heads/`),

  allocateBudget: (projectId: number, head_type: string, allocated_amount: string) =>
    http.post<ProjectBudgetHead>(`/api/v1/rspc/projects/${projectId}/heads/`, { head_type, allocated_amount }),

  disburseFund: (projectId: number, head_type: string, amount: string, reference_no: string, description: string) =>
    http.post<ProjectFundTransaction>(`/api/v1/rspc/projects/${projectId}/disburse/`, {
      head_type,
      amount,
      reference_no,
      description,
    }),

  getLedger: (projectId: number) =>
    http.get<ProjectFundTransaction[]>(`/api/v1/rspc/projects/${projectId}/ledger/`),
};
