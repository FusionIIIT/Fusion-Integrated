import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { http } from "../../../lib/http";
import type {
  ExpenseVoucherRequest,
  TAClaim,
  Anomaly,
  AuditObservation,
  DashboardSummary,
  IAAConfiguration,
} from "./types";

const KEY = "iaa";

export const keys = {
  requests: (status?: string) => [KEY, "requests", status] as const,
  request: (id: number) => [KEY, "request", id] as const,
  travelClaims: (status?: string) => [KEY, "travel", status] as const,
  travelClaim: (id: number) => [KEY, "travel", id] as const,
  anomalies: (status?: string) => [KEY, "anomalies", status] as const,
  auditObservations: (status?: string) => [KEY, "audit", status] as const,
  dashboard: () => [KEY, "dashboard"] as const,
  configuration: () => [KEY, "configuration"] as const,
};

export function useRequests(status?: string) {
  return useQuery({
    queryKey: keys.requests(status),
    queryFn: async () => {
      const resp = await http.get<ExpenseVoucherRequest[]>("/api/v1/iaa/requests/", {
        params: status ? { status } : undefined,
      });
      return resp.data;
    },
  });
}

export function useRequestDetail(id: number) {
  return useQuery({
    queryKey: keys.request(id),
    queryFn: async () => {
      const resp = await http.get<ExpenseVoucherRequest>(`/api/v1/iaa/requests/${id}/`);
      return resp.data;
    },
    enabled: !!id,
  });
}

export function useCreateRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      department: string;
      request_type: "expense" | "voucher";
      title: string;
      description?: string;
      items?: Array<{ description: string; category?: string; amount: number; receipt_reference?: string }>;
    }) => {
      const resp = await http.post<ExpenseVoucherRequest>("/api/v1/iaa/requests/", payload);
      return resp.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY, "requests"] });
    },
  });
}

export function useSubmitRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const resp = await http.post<ExpenseVoucherRequest>(`/api/v1/iaa/requests/${id}/submit/`);
      return resp.data;
    },
    onSuccess: (_, id) => {
      qc.invalidateQueries({ queryKey: keys.request(id) });
      qc.invalidateQueries({ queryKey: [KEY, "requests"] });
    },
  });
}

export function useDecideRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, decision, remarks }: { id: number; decision: "approve" | "reject"; remarks: string }) => {
      const resp = await http.post<ExpenseVoucherRequest>(`/api/v1/iaa/requests/${id}/decide/`, { decision, remarks });
      return resp.data;
    },
    onSuccess: (_, { id }) => {
      qc.invalidateQueries({ queryKey: keys.request(id) });
      qc.invalidateQueries({ queryKey: [KEY, "requests"] });
    },
  });
}

export function useTravelClaims(status?: string) {
  return useQuery({
    queryKey: keys.travelClaims(status),
    queryFn: async () => {
      const resp = await http.get<TAClaim[]>("/api/v1/iaa/travel/", {
        params: status ? { status } : undefined,
      });
      return resp.data;
    },
  });
}

export function useCreateTravelClaim() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      department: string;
      purpose: string;
      departure_date: string;
      arrival_date: string;
      source_location: string;
      destination_location: string;
      claimed_amount: number;
    }) => {
      const resp = await http.post<TAClaim>("/api/v1/iaa/travel/", payload);
      return resp.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY, "travel"] });
    },
  });
}

export function useAnomalies(status?: string) {
  return useQuery({
    queryKey: keys.anomalies(status),
    queryFn: async () => {
      const resp = await http.get<Anomaly[]>("/api/v1/iaa/anomalies/", {
        params: status ? { status } : undefined,
      });
      return resp.data;
    },
  });
}

export function useAuditObservations(status?: string) {
  return useQuery({
    queryKey: keys.auditObservations(status),
    queryFn: async () => {
      const resp = await http.get<AuditObservation[]>("/api/v1/iaa/audit/", {
        params: status ? { status } : undefined,
      });
      return resp.data;
    },
  });
}

export function useDashboardSummary() {
  return useQuery({
    queryKey: keys.dashboard(),
    queryFn: async () => {
      const resp = await http.get<DashboardSummary>("/api/v1/iaa/reports/");
      return resp.data;
    },
  });
}

export function useConfiguration() {
  return useQuery({
    queryKey: keys.configuration(),
    queryFn: async () => {
      const resp = await http.get<IAAConfiguration>("/api/v1/iaa/config/");
      return resp.data;
    },
  });
}
