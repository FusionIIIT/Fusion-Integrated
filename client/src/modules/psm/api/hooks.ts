/**
 * TanStack Query v5 custom hooks for Purchase and Stores Management (PSM).
 * Automatically invalidates relevant query keys on mutations.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { http, errorMessage } from "../../../lib/http";
import type {
  Indent,
  IndentVersion,
  Vendor,
  PurchaseOrder,
  GoodsReceiptNote,
  StockItem,
  StockTransfer,
  CreateIndentPayload,
  ModifyIndentPayload,
  UpdateIndentStatusPayload,
  CreateVendorPayload,
  CreatePOPayload,
  RecordGRNPayload,
  CreateTransferPayload,
} from "./types";

const KEY = "psm";

export const psmKeys = {
  all: [KEY] as const,
  indents: (filters?: { status?: string }) => [KEY, "indents", filters] as const,
  indent: (id: number) => [KEY, "indent", id] as const,
  indentVersions: (id: number) => [KEY, "indent", id, "versions"] as const,
  vendors: (filters?: { is_verified?: boolean }) => [KEY, "vendors", filters] as const,
  vendor: (id: number) => [KEY, "vendor", id] as const,
  purchaseOrders: () => [KEY, "purchaseOrders"] as const,
  grns: () => [KEY, "grns"] as const,
  stockItems: (department?: string) => [KEY, "stockItems", department] as const,
  stockTransfers: () => [KEY, "stockTransfers"] as const,
};

function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: [KEY] });
}

// ============================================================================
// Queries
// ============================================================================

export function useIndents(filters?: { status?: string }) {
  return useQuery({
    queryKey: psmKeys.indents(filters),
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters?.status) params.set("status", filters.status);
      const res = await http.get<Indent[]>(`/psm/indents/?${params.toString()}`);
      return res.data;
    },
  });
}

export function useIndentDetail(id?: number | null) {
  return useQuery({
    queryKey: psmKeys.indent(id ?? 0),
    queryFn: async () => {
      if (!id) return null;
      const res = await http.get<Indent>(`/psm/indents/${id}/`);
      return res.data;
    },
    enabled: Boolean(id),
  });
}

export function useIndentVersions(id?: number | null) {
  return useQuery({
    queryKey: psmKeys.indentVersions(id ?? 0),
    queryFn: async () => {
      if (!id) return [];
      const res = await http.get<IndentVersion[]>(`/psm/indents/${id}/versions/`);
      return res.data;
    },
    enabled: Boolean(id),
  });
}

export function useVendors(filters?: { is_verified?: boolean }) {
  return useQuery({
    queryKey: psmKeys.vendors(filters),
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters?.is_verified !== undefined) {
        params.set("is_verified", String(filters.is_verified));
      }
      const res = await http.get<Vendor[]>(`/psm/vendors/?${params.toString()}`);
      return res.data;
    },
  });
}

export function useVendorDetail(id?: number | null) {
  return useQuery({
    queryKey: psmKeys.vendor(id ?? 0),
    queryFn: async () => {
      if (!id) return null;
      const res = await http.get<Vendor>(`/psm/vendors/${id}/`);
      return res.data;
    },
    enabled: Boolean(id),
  });
}

export function usePurchaseOrders() {
  return useQuery({
    queryKey: psmKeys.purchaseOrders(),
    queryFn: async () => {
      const res = await http.get<PurchaseOrder[]>("/psm/purchase-orders/");
      return res.data;
    },
  });
}

export function useGoodsReceiptNotes() {
  return useQuery({
    queryKey: psmKeys.grns(),
    queryFn: async () => {
      const res = await http.get<GoodsReceiptNote[]>("/psm/grn/");
      return res.data;
    },
  });
}

export function useStockItems(department?: string) {
  return useQuery({
    queryKey: psmKeys.stockItems(department),
    queryFn: async () => {
      const params = new URLSearchParams();
      if (department) params.set("department", department);
      const res = await http.get<StockItem[]>(`/psm/stock-items/?${params.toString()}`);
      return res.data;
    },
  });
}

export function useStockTransfers() {
  return useQuery({
    queryKey: psmKeys.stockTransfers(),
    queryFn: async () => {
      const res = await http.get<StockTransfer[]>("/psm/transfers/");
      return res.data;
    },
  });
}

// ============================================================================
// Mutations
// ============================================================================

export function useCreateIndent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateIndentPayload) => {
      const res = await http.post<Indent>("/psm/indents/", payload);
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useModifyIndent(indentId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: ModifyIndentPayload) => {
      const res = await http.patch<Indent>(`/psm/indents/${indentId}/`, payload);
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useUpdateIndentStatus(indentId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: UpdateIndentStatusPayload) => {
      const res = await http.post<Indent>(`/psm/indents/${indentId}/transition/`, payload);
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useWithdrawIndent(indentId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const res = await http.post<Indent>(`/psm/indents/${indentId}/withdraw/`, {});
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useCreateVendor() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateVendorPayload) => {
      const res = await http.post<Vendor>("/psm/vendors/", payload);
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useVerifyVendor(vendorId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const res = await http.patch<Vendor>(`/psm/vendors/${vendorId}/`, { is_verified: true });
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useCreatePurchaseOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreatePOPayload) => {
      const res = await http.post<PurchaseOrder>("/psm/purchase-orders/", payload);
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useRecordGRN() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: RecordGRNPayload) => {
      const res = await http.post<GoodsReceiptNote>("/psm/grn/", payload);
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useCreateStockTransfer() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateTransferPayload) => {
      const res = await http.post<StockTransfer>("/psm/transfers/", payload);
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}
