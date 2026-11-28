import { http } from "../../lib/http";

export interface LeaveBalance {
  category: string;
  year: number;
  entitlement: string;
  opening_balance: string;
  available: string;
  pending: string;
  spendable: string;
}

export interface LeaveRequest {
  id: number;
  employee_user_id: number;
  category: string;
  starts_on: string;
  ends_on: string;
  chargeable_days: string;
  reason: string;
  status: string;
  assigned_stage: string;
  unit_head_recommendation: string;
}

export async function getBalances() {
  return (await http.get<LeaveBalance[]>("/elm/balances")).data;
}

export async function getRequests(queue = false) {
  return (await http.get<LeaveRequest[]>("/elm/requests", { params: queue ? { queue: "true" } : {} })).data;
}

export async function submitLeave(data: Record<string, unknown>) {
  return (await http.post<LeaveRequest>("/elm/requests", data)).data;
}

export async function requestAction(id: number, action: string, note = "", substitute_user_id?: number) {
  return (await http.post<LeaveRequest>(`/elm/requests/${id}`, { action, note, substitute_user_id })).data;
}

