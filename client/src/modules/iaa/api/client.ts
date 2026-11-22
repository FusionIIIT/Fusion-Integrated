import { http } from "../../../lib/http";

const API = "/iaa";

export interface Page<T> {
  results: T[];
  next: string | null;
  previous: string | null;
}

export interface IaaRecord {
  id: number;
  status: string;
  created_at: string;
  department?: string;
  amount?: string;
  description?: string;
  purpose?: string;
  request_type?: string;
  finding?: string;
  responses?: Array<{ id: number; corrective_action: string; satisfactory: boolean | null }>;
}

export interface ApprovalStep {
  id: number;
  record_type: "expense" | "ta";
  record_id: number;
  authority_role: string;
  due_at: string | null;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await http.request<T>({
    url: `${API}${path}`,
    method: init?.method ?? "GET",
    data: init?.body,
    headers: init?.headers as Record<string, string> | undefined,
  });
  return response.status === 204 ? (undefined as T) : response.data;
}
export const iaaApi = {
  expenses: () => request<Page<IaaRecord>>("/expenses?limit=50"),
  createExpense: (body: object) => request<IaaRecord>("/expenses", {
    method: "POST", body: JSON.stringify(body),
  }),
  submitExpense: (id: number) => request<IaaRecord>(`/expenses/${id}/submit`, { method: "POST" }),
  reviewExpense: (id: number, decision: "query" | "validate", text = "") => request<IaaRecord>(`/expenses/${id}/finance-review`, {
    method: "POST", body: JSON.stringify(decision === "query" ? { decision, clarification: text } : { decision, notes: text }),
  }),
  respond: (record_type: "expense" | "ta", id: number, response: string) => request<IaaRecord>(`/${record_type === "ta" ? "ta-claims" : "expenses"}/${id}/clarification-response`, {
    method: "POST", body: JSON.stringify({ response }),
  }),
  taClaims: () => request<Page<IaaRecord>>("/ta-claims?limit=50"),
  taClaim: (id: number) => request<IaaRecord>(`/ta-claims/${id}`),
  expense: (id: number) => request<IaaRecord>(`/expenses/${id}`),
  submitTaClaim: (body: object) => request<IaaRecord>("/ta-claims", {
    method: "POST", body: JSON.stringify(body),
  }),
  attachDocument: (kind: "expense" | "ta" | "observation", drive_url: string) => request<{ id: number }>("/documents", {
    method: "POST", body: JSON.stringify({ kind, drive_url }),
  }),
  approvals: () => request<Page<ApprovalStep>>("/approvals?limit=50"),
  decide: (id: number, decision: "approve" | "reject", remarks: string) =>
    request<IaaRecord>(`/approvals/${id}/decision`, {
      method: "POST", body: JSON.stringify({ decision, remarks }),
    }),
  reviewTa: (id: number, decision: "query" | "verify", text = "") => request<IaaRecord>(`/ta-claims/${id}/finance-review`, {
    method: "POST", body: JSON.stringify(decision === "query" ? { decision, clarification: text } : { decision, notes: text }),
  }),
  recordFinancialItem: (record_type: "expense" | "ta", id: number) => request<IaaRecord>(`/financial-records/${record_type}/${id}/record`, { method: "POST", body: "{}" }),
  anomalies: () => request<Page<{ id: number; record_type: string; record_id: number; category: string; description: string; status: string }>>("/anomalies?limit=50"),
  flagAnomaly: (body: object) => request<object>("/anomalies", { method: "POST", body: JSON.stringify(body) }),
  resolveAnomaly: (id: number, action: "resolve" | "escalate", remarks: string, next_resolver_user_id?: number, next_resolver_role?: string) => request<object>(`/anomalies/${id}/resolution`, {
    method: "POST", body: JSON.stringify({ action, remarks, next_resolver_user_id, next_resolver_role }),
  }),
  observations: () => request<Page<IaaRecord>>("/observations?limit=50"),
  createObservation: (body: object) => request<IaaRecord>("/observations/raise", { method: "POST", body: JSON.stringify(body) }),
  respondObservation: (id: number, corrective_action: string) => request<object>(`/observations/${id}/responses`, {
    method: "POST", body: JSON.stringify({ corrective_action }),
  }),
  reviewObservation: (id: number, response_id: number, satisfactory: boolean, remarks: string) => request<IaaRecord>(`/observations/${id}/responses/${response_id}/review`, {
    method: "POST", body: JSON.stringify({ satisfactory, remarks }),
  }),
  report: () => request<Record<string, Array<{ status: string; total: number }>>>("/reports/summary"),
  notifications: () => request<Page<{ id: string; event: string; record_type: string; record_id: number; created_at: string }>>("/notifications?limit=50"),
  policy: () => request<{ name: string; financial_year_start_month: number; ta_high_value_threshold: string | null; approval_timeout_hours: number | null; parameters: object } | null>("/configuration/policy"),
  updatePolicy: (body: object) => request<object>("/configuration/policy", { method: "PUT", body: JSON.stringify(body) }),
  approvalRoutes: () => request<Array<{ id: number; request_type: string; department: string; amount_from: string; amount_through: string | null; level: number; authority_role: string; assignee_user_id: number | null; timeout_hours: number | null; next_route: number | null; is_active: boolean }>>("/configuration/approval-routes"),
  addApprovalRoute: (body: object) => request<object>("/configuration/approval-routes", { method: "POST", body: JSON.stringify(body) }),
  budgets: () => request<Array<{ id: number; department: string; financial_year: string; budget_code: string; allocated_amount: string; committed_amount: string; available_amount: string }>>("/configuration/budgets"),
  addBudget: (body: object) => request<object>("/configuration/budgets", { method: "POST", body: JSON.stringify(body) }),
  exportReport: () => `${API}/reports/export`,
  history: (record_type: "expense" | "ta", id: number) =>
    request<Array<{ id: number; active_role: string; action: string; from_status: string; to_status: string; occurred_at: string }>>(`/${record_type}/${id}/history`),
};

