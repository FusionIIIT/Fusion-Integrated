import { http } from "../../lib/http";
import type { LeaveBalance, LeaveApplication, ApplyLeavePayload } from "./types";

export async function fetchMyBalances(): Promise<LeaveBalance[]> {
  const res = await http.get<LeaveBalance[]>("/elm/balances");
  return res.data;
}

export async function fetchMyApplications(): Promise<LeaveApplication[]> {
  const res = await http.get<LeaveApplication[]>("/elm/applications");
  return res.data;
}

export async function applyLeave(payload: ApplyLeavePayload): Promise<LeaveApplication> {
  const res = await http.post<LeaveApplication>("/elm/applications", payload);
  return res.data;
}

export async function cancelLeave(id: number): Promise<LeaveApplication> {
  const res = await http.post<LeaveApplication>(`/elm/applications/${id}/cancel`);
  return res.data;
}

export async function fetchPendingApprovals(): Promise<LeaveApplication[]> {
  const res = await http.get<LeaveApplication[]>("/elm/approvals/pending");
  return res.data;
}

export async function reviewLeave(
  id: number,
  recommend: boolean,
  comments: string = ""
): Promise<LeaveApplication> {
  const res = await http.post<LeaveApplication>(`/elm/approvals/${id}/review`, {
    recommend,
    comments,
  });
  return res.data;
}

export async function sanctionLeave(
  id: number,
  approve: boolean,
  comments: string = ""
): Promise<LeaveApplication> {
  const res = await http.post<LeaveApplication>(`/elm/approvals/${id}/sanction`, {
    approve,
    comments,
  });
  return res.data;
}
