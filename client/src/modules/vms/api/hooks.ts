/** TanStack Query hooks for VMS API. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { http } from "../../../lib/http";
import type { EmergencyMuster, GateAlert, Visit, VisitRequestPayload, QRScanPayload } from "./types";

const KEY = "vms";

export const keys = {
  visits: () => [KEY, "visits"] as const,
  alerts: () => [KEY, "alerts"] as const,
  muster: () => [KEY, "muster"] as const,
};

export function useVisits() {
  return useQuery({
    queryKey: keys.visits(),
    queryFn: async () => {
      const res = await http.get<Visit[]>("/api/v1/vms/visits/");
      return res.data;
    },
  });
}

export function useCreateVisit() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: VisitRequestPayload) => {
      const res = await http.post<Visit>("/api/v1/vms/visits/", payload);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.visits() });
    },
  });
}

export function useApproveVisit() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (visitId: number) => {
      const res = await http.post<Visit>(`/api/v1/vms/visits/${visitId}/approve/`);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.visits() });
    },
  });
}

export function useRejectVisit() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ visitId, reason }: { visitId: number; reason: string }) => {
      const res = await http.post<Visit>(`/api/v1/vms/visits/${visitId}/reject/`, { reason });
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.visits() });
    },
  });
}

export function useGateCheckIn() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: QRScanPayload) => {
      const res = await http.post<Visit>("/api/v1/vms/gate/check-in/", payload);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.visits() });
    },
  });
}

export function useGateCheckOut() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (visitId: number) => {
      const res = await http.post<Visit>("/api/v1/vms/gate/check-out/", { visit_id: visitId });
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.visits() });
    },
  });
}

export function useGateAlerts() {
  return useQuery({
    queryKey: keys.alerts(),
    queryFn: async () => {
      const res = await http.get<GateAlert[]>("/api/v1/vms/security/alerts/");
      return res.data;
    },
  });
}

export function useTriggerMuster() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const res = await http.post<EmergencyMuster>("/api/v1/vms/emergency/muster/");
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.muster() });
      qc.invalidateQueries({ queryKey: keys.alerts() });
    },
  });
}
