/** React Query hooks for VMS API. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { http } from "../../../lib/http";
import type {
  VisitRequest,
  Pass,
  BlacklistEntry,
  MusterResponse,
  DashboardMetrics,
  GateCheckLog,
  AccessPolicy,
  PreAuthorization,
} from "./types";

const KEYS = {
  visits: ["vms", "visits"] as const,
  liveVisitors: ["vms", "live-visitors"] as const,
  blacklist: ["vms", "blacklist"] as const,
  emergency: ["vms", "emergency"] as const,
  analytics: ["vms", "analytics"] as const,
  audit: ["vms", "audit"] as const,
  policies: ["vms", "policies"] as const,
  preauth: ["vms", "preauth"] as const,
};

export function useVisits(params?: { status?: string; search?: string; host_id?: number }) {
  return useQuery({
    queryKey: [...KEYS.visits, params],
    queryFn: async () => {
      const { data } = await http.get<VisitRequest[]>("/vms/visits/", { params });
      return data;
    },
  });
}

export function useLiveVisitors() {
  return useQuery({
    queryKey: KEYS.liveVisitors,
    queryFn: async () => {
      const { data } = await http.get<VisitRequest[]>("/vms/dashboard/live/");
      return data;
    },
  });
}

export function usePreRegisterVisit() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      name: string;
      email: string;
      phone: string;
      organization?: string;
      id_document_type: string;
      id_document_number: string;
      host_id: number;
      purpose: string;
      scheduled_start: string;
      scheduled_end: string;
      access_zones?: string[];
      is_urgent_exception?: boolean;
    }) => {
      const { data } = await http.post<VisitRequest>("/vms/visits/pre-register/", payload);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.visits });
    },
  });
}

export function useWalkInRegister() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      name: string;
      email: string;
      phone: string;
      organization?: string;
      id_document_type: string;
      id_document_number: string;
      host_id: number;
      purpose: string;
      duration_hours?: number;
      auto_approve?: boolean;
    }) => {
      const { data } = await http.post<VisitRequest>("/vms/visits/walk-in/", payload);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.visits });
      qc.invalidateQueries({ queryKey: KEYS.liveVisitors });
    },
  });
}

export function useDecideVisit() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, decision, reason }: { id: number; decision: "APPROVE" | "REJECT"; reason?: string }) => {
      const { data } = await http.post<VisitRequest>(`/vms/visits/${id}/decide/`, { decision, reason });
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.visits });
    },
  });
}

export function useContingencyApprove() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, reason }: { id: number; reason: string }) => {
      const { data } = await http.post<VisitRequest>(`/vms/visits/${id}/contingency-approve/`, { reason });
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.visits });
    },
  });
}

export function useExtendVisit() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, hours, reason }: { id: number; hours: number; reason?: string }) => {
      const { data } = await http.post<VisitRequest>(`/vms/visits/${id}/extend/`, { hours, reason });
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.visits });
      qc.invalidateQueries({ queryKey: KEYS.liveVisitors });
    },
  });
}

export function useTerminateVisit() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, reason }: { id: number; reason: string }) => {
      const { data } = await http.post<VisitRequest>(`/vms/visits/${id}/terminate/`, { reason });
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.visits });
      qc.invalidateQueries({ queryKey: KEYS.liveVisitors });
    },
  });
}

export function useValidatePass() {
  return useMutation({
    mutationFn: async ({ qr_token, gate_name }: { qr_token: string; gate_name?: string }) => {
      const { data } = await http.post<{ is_valid: boolean; message: string; pass: Pass | null }>("/vms/gate/validate/", {
        qr_token,
        gate_name,
      });
      return data;
    },
  });
}

export function useGateCheckIn() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ pass_id, gate_name }: { pass_id: number; gate_name?: string }) => {
      const { data } = await http.post<GateCheckLog>("/vms/gate/check-in/", { pass_id, gate_name });
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.visits });
      qc.invalidateQueries({ queryKey: KEYS.liveVisitors });
      qc.invalidateQueries({ queryKey: KEYS.audit });
    },
  });
}

export function useGateCheckOut() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ pass_id, gate_name }: { pass_id: number; gate_name?: string }) => {
      const { data } = await http.post<GateCheckLog>("/vms/gate/check-out/", { pass_id, gate_name });
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.visits });
      qc.invalidateQueries({ queryKey: KEYS.liveVisitors });
      qc.invalidateQueries({ queryKey: KEYS.audit });
    },
  });
}

export function useGateOverride() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ pass_id, reason, gate_name }: { pass_id: number; reason: string; gate_name?: string }) => {
      const { data } = await http.post<GateCheckLog>("/vms/gate/override/", { pass_id, reason, gate_name });
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.visits });
      qc.invalidateQueries({ queryKey: KEYS.liveVisitors });
      qc.invalidateQueries({ queryKey: KEYS.audit });
    },
  });
}

export function useBlacklist(status?: string) {
  return useQuery({
    queryKey: [...KEYS.blacklist, status],
    queryFn: async () => {
      const { data } = await http.get<BlacklistEntry[]>("/vms/blacklist/", { params: { status } });
      return data;
    },
  });
}

export function useAddBlacklist() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      name: string;
      id_document_type: string;
      id_document_number: string;
      phone?: string;
      reason: string;
    }) => {
      const { data } = await http.post<BlacklistEntry>("/vms/blacklist/", payload);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.blacklist });
    },
  });
}

export function useSafeList() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, hours, reason }: { id: number; hours: number; reason: string }) => {
      const { data } = await http.post<BlacklistEntry>(`/vms/blacklist/${id}/safe-list/`, { hours, reason });
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.blacklist });
    },
  });
}

export function useTriggerMuster() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ assembly_point }: { assembly_point?: string }) => {
      const { data } = await http.post<{ muster_id: string; status: string }>("/vms/emergency/muster/", {
        assembly_point,
      });
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.emergency });
    },
  });
}

export function useEmergencyRoster() {
  return useQuery({
    queryKey: KEYS.emergency,
    queryFn: async () => {
      const { data } = await http.get<MusterResponse>("/vms/emergency/roster/");
      return data;
    },
  });
}

export function useRollCall() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, status, notes }: { id: number; status: "ACCOUNTED" | "UNACCOUNTED"; notes?: string }) => {
      const { data } = await http.post(`/vms/emergency/roll-call/${id}/`, { status, notes });
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.emergency });
    },
  });
}

export function useAnalytics() {
  return useQuery({
    queryKey: KEYS.analytics,
    queryFn: async () => {
      const { data } = await http.get<DashboardMetrics>("/vms/analytics/dashboard/");
      return data;
    },
  });
}

export function useAuditLogs() {
  return useQuery({
    queryKey: KEYS.audit,
    queryFn: async () => {
      const { data } = await http.get<GateCheckLog[]>("/vms/audit/");
      return data;
    },
  });
}

export function usePolicies() {
  return useQuery({
    queryKey: KEYS.policies,
    queryFn: async () => {
      const { data } = await http.get<AccessPolicy[]>("/vms/policies/");
      return data;
    },
  });
}

export function usePreAuthorizations() {
  return useQuery({
    queryKey: KEYS.preauth,
    queryFn: async () => {
      const { data } = await http.get<PreAuthorization[]>("/vms/pre-authorizations/");
      return data;
    },
  });
}
