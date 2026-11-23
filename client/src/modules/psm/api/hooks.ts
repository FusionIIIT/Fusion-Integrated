// TanStack Query hooks for PSM using the shared HTTP client.
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { filenameFromDisposition, saveBlob } from "../../../lib/download";
import { http, readBlobError } from "../../../lib/http";
import type {
  AuditLog,
  DashboardSummary,
  DiscrepancyCase,
  GoodsReceiptNote,
  Indent,
  IndentDetail,
  InternalIssue,
  Invoice,
  ListResult,
  Page,
  PaymentTransaction,
  PsmNotification,
  PsmPolicy,
  PurchaseOrder,
  ReportGenerationLog,
  ReportResult,
  ReportSchedule,
  StockAvailability,
  StockItem,
  StockLocation,
  StockTransfer,
  Tender,
  Vendor,
} from "./types";

const KEY = "psm";

export const psmKeys = {
  dashboard: () => [KEY, "dashboard"] as const,
  indents: (f?: unknown) => [KEY, "indents", f] as const,
  indent: (id: number) => [KEY, "indent", id] as const,
  stockItems: () => [KEY, "stock-items"] as const,
  stockLocations: () => [KEY, "stock-locations"] as const,
  stockAvailability: (f?: unknown) => [KEY, "stock-availability", f] as const,
  internalIssues: () => [KEY, "internal-issues"] as const,
  transfers: () => [KEY, "transfers"] as const,
  vendors: () => [KEY, "vendors"] as const,
  tenders: () => [KEY, "tenders"] as const,
  purchaseOrders: () => [KEY, "purchase-orders"] as const,
  grns: () => [KEY, "grns"] as const,
  discrepancies: () => [KEY, "discrepancies"] as const,
  invoices: () => [KEY, "invoices"] as const,
  reportSchedules: () => [KEY, "report-schedules"] as const,
  reportLogs: () => [KEY, "report-logs"] as const,
  audit: (f?: unknown) => [KEY, "audit", f] as const,
  notifications: () => [KEY, "notifications"] as const,
  policy: () => [KEY, "policy"] as const,
};

function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: [KEY] });
}

export function usePsmDashboard() {
  return useQuery({
    queryKey: psmKeys.dashboard(),
    queryFn: async () => (await http.get<DashboardSummary>("/psm/dashboard")).data,
  });
}

export function usePsmNotifications() {
  return useQuery({
    queryKey: psmKeys.notifications(),
    queryFn: async () => (await http.get<Page<PsmNotification>>("/psm/notifications")).data,
  });
}

export function useIndents(params?: { status?: string; department?: string; queue?: string }) {
  return useQuery({
    queryKey: psmKeys.indents(params),
    queryFn: async () => (await http.get<Page<Indent>>("/psm/indents", { params })).data,
  });
}

export function useIndentDetail(id: number | null) {
  return useQuery({
    queryKey: psmKeys.indent(id ?? 0),
    queryFn: async () => (await http.get<IndentDetail>(`/psm/indents/${id}`)).data,
    enabled: id != null,
  });
}

export function useCreateIndent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) => (await http.post<Indent>("/psm/indents", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useModifyIndent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, body }: { id: number; body: Record<string, unknown> }) =>
      (await http.patch<Indent>(`/psm/indents/${id}`, body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useIndentAction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, action, body = {} }: { id: number; action: string; body?: Record<string, unknown> }) =>
      (await http.post<Indent>(`/psm/indents/${id}/${action}`, body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useStockItems() {
  return useQuery({
    queryKey: psmKeys.stockItems(),
    queryFn: async () => (await http.get<Page<StockItem>>("/psm/stock/items")).data,
  });
}

export function useStockLocations() {
  return useQuery({
    queryKey: psmKeys.stockLocations(),
    queryFn: async () => (await http.get<ListResult<StockLocation>>("/psm/stock/locations")).data,
  });
}

export function useStockAvailability(params?: { item_id?: number; location_id?: number }) {
  return useQuery({
    queryKey: psmKeys.stockAvailability(params),
    queryFn: async () => (await http.get<ListResult<StockAvailability>>("/psm/stock/availability", { params })).data,
  });
}

export function useCreateStockItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) => (await http.post<StockItem>("/psm/stock/items", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useCreateStockLocation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) =>
      (await http.post<StockLocation>("/psm/stock/locations", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useRecordStockAdjustment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) => (await http.post("/psm/stock/adjustments", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useInternalIssues() {
  return useQuery({
    queryKey: psmKeys.internalIssues(),
    queryFn: async () => (await http.get<Page<InternalIssue>>("/psm/internal-issues")).data,
  });
}

export function useInternalIssueAction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, action, body = {} }: { id: number; action: string; body?: Record<string, unknown> }) =>
      (await http.post<InternalIssue>(`/psm/internal-issues/${id}/${action}`, body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useTransfers() {
  return useQuery({
    queryKey: psmKeys.transfers(),
    queryFn: async () => (await http.get<Page<StockTransfer>>("/psm/transfers")).data,
  });
}

export function useCreateTransfer() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) => (await http.post<StockTransfer>("/psm/transfers", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useTransferAction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, action }: { id: number; action: string }) =>
      (await http.post<StockTransfer>(`/psm/transfers/${id}/${action}`, {})).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useVendors() {
  return useQuery({
    queryKey: psmKeys.vendors(),
    queryFn: async () => (await http.get<Page<Vendor>>("/psm/vendors")).data,
  });
}

export function useCreateVendor() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) => (await http.post<Vendor>("/psm/vendors", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useVerifyVendor() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => (await http.post<Vendor>(`/psm/vendors/${id}/verify`, {})).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useTenders() {
  return useQuery({
    queryKey: psmKeys.tenders(),
    queryFn: async () => (await http.get<Page<Tender>>("/psm/tenders")).data,
  });
}

export function useCreateTender() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) => (await http.post<Tender>("/psm/tenders", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useTenderAction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, action, body = {} }: { id: number; action: string; body?: Record<string, unknown> }) =>
      (await http.post(`/psm/tenders/${id}/${action}`, body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function usePurchaseOrders() {
  return useQuery({
    queryKey: psmKeys.purchaseOrders(),
    queryFn: async () => (await http.get<Page<PurchaseOrder>>("/psm/purchase-orders")).data,
  });
}

export function useCreatePurchaseOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) =>
      (await http.post<PurchaseOrder>("/psm/purchase-orders", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useUpdatePurchaseOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, body }: { id: number; body: Record<string, unknown> }) =>
      (await http.patch<PurchaseOrder>(`/psm/purchase-orders/${id}`, body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useGrns() {
  return useQuery({
    queryKey: psmKeys.grns(),
    queryFn: async () => (await http.get<Page<GoodsReceiptNote>>("/psm/grns")).data,
  });
}

export function useCreateGrn() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) => (await http.post<GoodsReceiptNote>("/psm/grns", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useConfirmGrn() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => (await http.post<GoodsReceiptNote>(`/psm/grns/${id}/confirm`, {})).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useDiscrepancies() {
  return useQuery({
    queryKey: psmKeys.discrepancies(),
    queryFn: async () => (await http.get<Page<DiscrepancyCase>>("/psm/discrepancies")).data,
  });
}

export function useCreateDiscrepancy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) =>
      (await http.post<DiscrepancyCase>("/psm/discrepancies", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useResolveDiscrepancy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, body }: { id: number; body: Record<string, unknown> }) =>
      (await http.post<DiscrepancyCase>(`/psm/discrepancies/${id}/resolve`, body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useInvoices() {
  return useQuery({
    queryKey: psmKeys.invoices(),
    queryFn: async () => (await http.get<Page<Invoice>>("/psm/invoices")).data,
  });
}

export function useCreateInvoice() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) => (await http.post<Invoice>("/psm/invoices", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useInvoiceAction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, action, body = {} }: { id: number; action: string; body?: Record<string, unknown> }) =>
      (await http.post<Invoice | PaymentTransaction>(`/psm/invoices/${id}/${action}`, body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useGenerateReport() {
  return useMutation({
    mutationFn: async (body: { report_type: string; filters?: Record<string, string> }) =>
      (await http.post<ReportResult>("/psm/reports/generate", body)).data,
  });
}

export function useExportReportCsv() {
  return useMutation({
    mutationFn: async (body: { report_type: string; filters?: Record<string, string> }) => {
      try {
        const res = await http.post<Blob>("/psm/reports/export", body, { responseType: "blob" });
        const name = filenameFromDisposition(
          res.headers["content-disposition"] as string | undefined,
          `psm-${body.report_type}-report.csv`,
        );
        saveBlob(res.data, name);
      } catch (err) {
        throw await readBlobError(err);
      }
    },
  });
}

export function useReportSchedules() {
  return useQuery({
    queryKey: psmKeys.reportSchedules(),
    queryFn: async () => (await http.get<Page<ReportSchedule>>("/psm/reports/schedules")).data,
  });
}

export function useCreateReportSchedule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) =>
      (await http.post<ReportSchedule>("/psm/reports/schedules", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useRunReportSchedule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await http.post<ReportGenerationLog>(`/psm/reports/schedules/${id}/run`, {})).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useReportLogs() {
  return useQuery({
    queryKey: psmKeys.reportLogs(),
    queryFn: async () => (await http.get<Page<ReportGenerationLog>>("/psm/reports/logs")).data,
  });
}

export function useAuditLogs(targetType?: string) {
  return useQuery({
    queryKey: psmKeys.audit(targetType),
    queryFn: async () =>
      (await http.get<Page<AuditLog>>("/psm/audit", { params: targetType ? { target_type: targetType } : undefined })).data,
  });
}

export function usePsmPolicies() {
  return useQuery({
    queryKey: psmKeys.policy(),
    queryFn: async () => (await http.get<ListResult<PsmPolicy>>("/psm/policy")).data,
  });
}

export function usePublishPolicy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) => (await http.post<PsmPolicy>("/psm/policy", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}
