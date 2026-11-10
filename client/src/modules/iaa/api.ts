import { http } from "../../lib/http";

export const roles = ["Basic User", "Finance Staff", "HoD", "Dean", "Director", "Auditor", "System Admin"];
export const authorities = ["HoD", "Dean", "Director"];
export type Row = Record<string, unknown> & { id: number };
export interface RequestRow extends Row {
  kind: string; status: string; department: string; amount: string | null;
  description: string; request_type: string; documents: string[];
  creator_id: number; assignee_id: number | null; assignee_role: string;
  history?: Row[]; clarifications?: Row[]; anomalies?: Row[]; observations?: Row[];
}
export const label = (s: string) => s.replaceAll("_", " ").replace(/^./, c => c.toUpperCase());
export function headers(role: string) { return { "X-IAA-Role": role }; }
export async function get<T>(path: string, role: string): Promise<T> {
  return (await http.get<T>(`/iaa/${path}`, { headers: headers(role) })).data;
}
export async function post<T>(path: string, role: string, body: unknown): Promise<T> {
  return (await http.post<T>(`/iaa/${path}`, body, { headers: headers(role) })).data;
}
export const evidenceLinks = (text: string) => text.split(/\r?\n/).map(s => s.trim()).filter(Boolean);

export function requestActions(row: RequestRow, role: string, userId: number): string[] {
  if (role === "Basic User" && row.creator_id === userId) {
    if (row.status === "draft") return ["edit", "submit"];
    if (row.status === "query_raised") return ["respond"];
  }
  if (role === "Finance Staff") {
    if (["submitted", "query_responded"].includes(row.status))
      return ["query", "validate", ...(row.kind === "ta" ? ["reject_ta"] : []), "anomaly"];
    if (["approved", "verified"].includes(row.status)) return ["record", "anomaly"];
  }
  if (authorities.includes(role) && row.assignee_id === userId && row.creator_id !== userId
      && row.assignee_role === role
      && ["finance_validated", "approval_pending", "escalated"].includes(row.status))
    return ["approve", "reject"];
  if (role === "Auditor" && row.status !== "draft") return ["observation", "anomaly"];
  return [];
}
