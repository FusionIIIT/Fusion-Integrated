import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { http } from "../../../lib/http";
import type {
  DiscrepancyReport,
  GoodsReceiptNote,
  Indent,
  ItemMaster,
  PurchaseOrder,
  StockItem,
  Vendor,
} from "./types";

const KEY = "psm";

export const keys = {
  indents: () => [KEY, "indents"] as const,
  indent: (id: number) => [KEY, "indent", id] as const,
  vendors: () => [KEY, "vendors"] as const,
  purchaseOrders: () => [KEY, "purchase-orders"] as const,
  goodsReceipts: () => [KEY, "goods-receipts"] as const,
  stock: () => [KEY, "stock"] as const,
  discrepancies: () => [KEY, "discrepancies"] as const,
  items: () => [KEY, "items"] as const,
};

function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: [KEY] });
}

// -- Indents -------------------------------------------------------------------
export function useIndents() {
  return useQuery({
    queryKey: keys.indents(),
    queryFn: async () => {
      const { data } = await http.get<Indent[]>("/psm/indents");
      return data;
    },
  });
}

export function useIndent(id: number) {
  return useQuery({
    queryKey: keys.indent(id),
    queryFn: async () => {
      const { data } = await http.get<Indent>(`/psm/indents/${id}`);
      return data;
    },
    enabled: Boolean(id),
  });
}

export function useCreateIndent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      department_code: string;
      title: string;
      purpose: string;
      priority: string;
      items: {
        item_master_id: number;
        quantity_requested: number;
        estimated_unit_cost: string;
        specifications?: string;
      }[];
    }) => {
      const { data } = await http.post<Indent>("/psm/indents", payload);
      return data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useSubmitIndent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const { data } = await http.post<Indent>(`/psm/indents/${id}/submit`);
      return data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useReviewDeptIndent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, action, remarks }: { id: number; action: string; remarks?: string }) => {
      const { data } = await http.post<Indent>(`/psm/indents/${id}/dept-action`, { action, remarks });
      return data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useReviewPSIndent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, action, remarks }: { id: number; action: string; remarks?: string }) => {
      const { data } = await http.post<Indent>(`/psm/indents/${id}/ps-action`, { action, remarks });
      return data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useReviewDirectorIndent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, action, remarks }: { id: number; action: string; remarks?: string }) => {
      const { data } = await http.post<Indent>(`/psm/indents/${id}/director-action`, { action, remarks });
      return data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useCancelIndent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const { data } = await http.post<Indent>(`/psm/indents/${id}/cancel`);
      return data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Vendors -------------------------------------------------------------------
export function useVendors() {
  return useQuery({
    queryKey: keys.vendors(),
    queryFn: async () => {
      const { data } = await http.get<Vendor[]>("/psm/vendors");
      return data;
    },
  });
}

export function useRegisterVendor() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<Vendor>) => {
      const { data } = await http.post<Vendor>("/psm/vendors", payload);
      return data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useVerifyVendor() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const { data } = await http.post<Vendor>(`/psm/vendors/${id}/verify`);
      return data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Purchase Orders -----------------------------------------------------------
export function usePurchaseOrders() {
  return useQuery({
    queryKey: keys.purchaseOrders(),
    queryFn: async () => {
      const { data } = await http.get<PurchaseOrder[]>("/psm/purchase-orders");
      return data;
    },
  });
}

export function useCreatePurchaseOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { indent_id: number; vendor_id: number; delivery_due_date?: string }) => {
      const { data } = await http.post<PurchaseOrder>("/psm/purchase-orders", payload);
      return data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useIssuePurchaseOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const { data } = await http.post<PurchaseOrder>(`/psm/purchase-orders/${id}/issue`);
      return data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Goods Receipts ------------------------------------------------------------
export function useGoodsReceipts() {
  return useQuery({
    queryKey: keys.goodsReceipts(),
    queryFn: async () => {
      const { data } = await http.get<GoodsReceiptNote[]>("/psm/goods-receipts");
      return data;
    },
  });
}

export function useCreateGoodsReceipt() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      po_id: number;
      receipt_date: string;
      challan_number?: string;
      invoice_number?: string;
      items: {
        po_line_item_id: number;
        quantity_received: number;
        quantity_accepted: number;
        quantity_rejected: number;
        remarks?: string;
      }[];
    }) => {
      const { data } = await http.post<GoodsReceiptNote>("/psm/goods-receipts", payload);
      return data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useAcknowledgeGoodsReceipt() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const { data } = await http.post<GoodsReceiptNote>(`/psm/goods-receipts/${id}/acknowledge`);
      return data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Stock & Inventory ---------------------------------------------------------
export function useStock() {
  return useQuery({
    queryKey: keys.stock(),
    queryFn: async () => {
      const { data } = await http.get<StockItem[]>("/psm/stock");
      return data;
    },
  });
}

export function useFulfillStock() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (indentId: number) => {
      const { data } = await http.post<Indent>("/psm/stock/fulfill", { indent_id: indentId });
      return data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Discrepancies -------------------------------------------------------------
export function useDiscrepancies() {
  return useQuery({
    queryKey: keys.discrepancies(),
    queryFn: async () => {
      const { data } = await http.get<DiscrepancyReport[]>("/psm/discrepancies");
      return data;
    },
  });
}

export function useResolveDiscrepancy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, resolution_summary }: { id: number; resolution_summary: string }) => {
      const { data } = await http.post<DiscrepancyReport>(`/psm/discrepancies/${id}/resolve`, {
        resolution_summary,
      });
      return data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Items ---------------------------------------------------------------------
export function useItems() {
  return useQuery({
    queryKey: keys.items(),
    queryFn: async () => {
      const { data } = await http.get<ItemMaster[]>("/psm/items");
      return data;
    },
  });
}
