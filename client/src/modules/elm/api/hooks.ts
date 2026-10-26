import { useState, useEffect, useCallback } from "react";
import { http } from "../../../lib/http";
import type { LeaveRequest, LeaveBalance, ApplyLeavePayload } from "./types";

function errorMessage(error: any): string {
  const responseError = error?.response?.data?.error;
  return responseError?.message ?? responseError ?? error?.message ?? "Request failed.";
}

export function useMyLeaves() {
  const [leaves, setLeaves] = useState<LeaveRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchLeaves = useCallback(async () => {
    try {
      setLoading(true);
      const res = await http.get<LeaveRequest[]>("/api/v1/elm/leaves/");
      setLeaves(res.data);
      setError(null);
    } catch (err: any) {
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
      const res = await http.get<LeaveBalance[]>("/api/v1/elm/balances/");
      setBalances(res.data);
      setError(null);
    } catch (err: any) {
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
      const res = await http.get<LeaveRequest[]>("/api/v1/elm/substitute-queue/");
      setRequests(res.data);
      setError(null);
    } catch (err: any) {
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
      const res = await http.get<LeaveRequest[]>("/api/v1/elm/approvals/");
      setRequests(res.data);
      setError(null);
    } catch (err: any) {
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

export function useAuthorityApprovalsQueue() {
  const [requests, setRequests] = useState<LeaveRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchQueue = useCallback(async () => {
    try {
      setLoading(true);
      const res = await http.get<LeaveRequest[]>("/api/v1/elm/authority-approvals/");
      setRequests(res.data);
      setError(null);
    } catch (err: any) {
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
  const res = await http.post<LeaveRequest>("/api/v1/elm/leaves/", payload);
  return res.data;
}

export async function decideSubstitute(leaveId: string, accept: boolean, remarks: string = ""): Promise<LeaveRequest> {
  const res = await http.post<LeaveRequest>(`/api/v1/elm/substitute-queue/${leaveId}/decision/`, { accept, remarks });
  return res.data;
}

export async function decideApproval(leaveId: string, approve: boolean, remarks: string = "", forwardHigher: boolean = false): Promise<LeaveRequest> {
  const res = await http.post<LeaveRequest>(`/api/v1/elm/approvals/${leaveId}/decision/`, {
    approve,
    remarks,
    forward_higher: forwardHigher,
  });
  return res.data;
}

export async function withdrawLeaveRequest(leaveId: string, reason: string = ""): Promise<LeaveRequest> {
  const res = await http.post<LeaveRequest>(`/api/v1/elm/leaves/${leaveId}/withdraw/`, { reason });
  return res.data;
}

export async function nominateReplacement(leaveId: string, substituteId: string): Promise<LeaveRequest> {
  const res = await http.post<LeaveRequest>(`/api/v1/elm/leaves/${leaveId}/replacement-substitute/`, {
    substitute_id: substituteId,
  });
  return res.data;
}

export async function decideAuthority(leaveId: string, approve: boolean, remarks: string = ""): Promise<LeaveRequest> {
  const res = await http.post<LeaveRequest>(`/api/v1/elm/authority-approvals/${leaveId}/decision/`, {
    approve,
    remarks,
  });
  return res.data;
}
