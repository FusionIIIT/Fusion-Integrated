import { useState, useEffect, useCallback } from "react";
import { saveBlob } from "../../../lib/download";
import { http, errorMessage, readBlobError } from "../../../lib/http";
import type { LeaveRequest, LeaveBalance, ApplyLeavePayload } from "./types";

export function useMyLeaves() {
  const [leaves, setLeaves] = useState<LeaveRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchLeaves = useCallback(async () => {
    try {
      setLoading(true);
      const res = await http.get<LeaveRequest[]>("/elm/leaves/");
      setLeaves(res.data);
      setError(null);
    } catch (err: unknown) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLeaves();
  }, [fetchLeaves]);

  return { leaves, loading, error, refetch: fetchLeaves };
}

export function useLeaveBalances() {
  const [balances, setBalances] = useState<LeaveBalance[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchBalances = useCallback(async () => {
    try {
      setLoading(true);
      const res = await http.get<LeaveBalance[]>("/elm/balances/");
      setBalances(res.data);
      setError(null);
    } catch (err: unknown) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchBalances();
  }, [fetchBalances]);

  return { balances, loading, error, refetch: fetchBalances };
}

export function useSubstituteQueue() {
  const [requests, setRequests] = useState<LeaveRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchQueue = useCallback(async () => {
    try {
      setLoading(true);
      const res = await http.get<LeaveRequest[]>("/elm/substitute-queue/");
      setRequests(res.data);
      setError(null);
    } catch (err: unknown) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchQueue();
  }, [fetchQueue]);

  return { requests, loading, error, refetch: fetchQueue };
}

export function useApprovalsQueue() {
  const [requests, setRequests] = useState<LeaveRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchQueue = useCallback(async () => {
    try {
      setLoading(true);
      const res = await http.get<LeaveRequest[]>("/elm/approvals/");
      setRequests(res.data);
      setError(null);
    } catch (err: unknown) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchQueue();
  }, [fetchQueue]);

  return { requests, loading, error, refetch: fetchQueue };
}

export async function submitLeave(payload: ApplyLeavePayload): Promise<LeaveRequest> {
  const res = await http.post<LeaveRequest>("/elm/leaves/", payload);
  return res.data;
}

export async function decideSubstitute(leaveId: string, accept: boolean, remarks: string = ""): Promise<LeaveRequest> {
  const res = await http.post<LeaveRequest>(`/elm/substitute-queue/${leaveId}/decision/`, { accept, remarks });
  return res.data;
}

export async function decideApproval(leaveId: string, approve: boolean, remarks: string = "", forwardHigher: boolean = false): Promise<LeaveRequest> {
  const res = await http.post<LeaveRequest>(`/elm/approvals/${leaveId}/decision/`, {
    approve,
    remarks,
    forward_higher: forwardHigher,
  });
  return res.data;
}

export async function withdrawLeaveRequest(leaveId: string, reason: string = ""): Promise<LeaveRequest> {
  const res = await http.post<LeaveRequest>(`/elm/leaves/${leaveId}/withdraw/`, { reason });
  return res.data;
}

export async function followupLeave(id: string, kind: string, data: {reason: string; end_date?: string; substitute_id?: string}) {
  return (await http.post<LeaveRequest>(`/elm/leaves/${id}/${kind}/`, data)).data;
}
export async function replaceSubstitute(id: string, substitute_id: string) {
  return (await http.post<LeaveRequest>(`/elm/leaves/${id}/replace-substitute/`, {substitute_id})).data;
}
export async function exportLeave(id: string) {
  try {
    const response = await http.get(`/elm/leaves/${id}/export/`, { responseType: "blob" });
    saveBlob(response.data, `leave-${id}.html`);
  } catch (error) { throw await readBlobError(error); }
}
