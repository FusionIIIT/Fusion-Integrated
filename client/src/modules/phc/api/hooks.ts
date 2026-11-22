/** Every mutation invalidates the keys it can affect; the server enforces roles. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { filenameFromDisposition, saveBlob } from "../../../lib/download";
import { http, readBlobError } from "../../../lib/http";
import type {
  AdminReport, AmbulanceLog, AmbulanceLogCreate, AuditLog, ClaimDecision,
  ClaimTransition, DoctorAttendance, DoctorAttendanceMark, DoctorSchedule,
  DoctorScheduleCreate, DoctorScheduleUpdate, HealthAdvisory,
  HealthAdvisoryCreate, InventoryItem, InventoryItemCreate, Page, Patient,
  Prescription, PrescriptionCreate, ReimbursementClaim,
  ReimbursementClaimCreate, Requisition, RequisitionCreate, RequisitionDecision,
  ReportCategory, ScheduleResponse, StockAdjustment, StockAdjustmentCreate,
  Visit, VisitCreate,
} from "./types";

const KEY = "phc";

export const keys = {
  schedule: () => [KEY, "schedule"] as const,
  patients: (q?: string) => [KEY, "patients", q] as const,
  records: () => [KEY, "records"] as const,
  prescriptions: () => [KEY, "prescriptions"] as const,
  claims: () => [KEY, "claims"] as const,
  inventory: () => [KEY, "inventory"] as const,
  advisories: () => [KEY, "advisories"] as const,
  report: (category: string) => [KEY, "report", category] as const,
  auditLog: (limit: number) => [KEY, "audit-log", limit] as const,
};

/** Coarse invalidation: correctness beats shaving a refetch on these pages. */
function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: [KEY] });
}

// -- Doctor schedule & attendance ----------------------------------------------
export function useSchedule(enabled = true) {
  return useQuery({
    queryKey: keys.schedule(),
    queryFn: async () =>
      (await http.get<ScheduleResponse>("/phc/schedule")).data,
    enabled,
    staleTime: 30_000,
  });
}

export function useCreateSchedule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: DoctorScheduleCreate) =>
      (await http.post<DoctorSchedule>("/phc/staff/schedule", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useMaintainSchedule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...body }: DoctorScheduleUpdate & { id: number }) =>
      (await http.patch<DoctorSchedule>(`/phc/staff/schedule/${id}`, body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function usePublishSchedule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await http.post<DoctorSchedule>(
        `/phc/staff/schedule/${id}/publish`, {})).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useMarkAttendance() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: DoctorAttendanceMark) =>
      (await http.post<DoctorAttendance>("/phc/staff/attendance", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Patient records & prescriptions -------------------------------------------
export function usePatientSearch(q: string) {
  return useQuery({
    queryKey: keys.patients(q),
    queryFn: async () =>
      (await http.get<Page<Patient>>("/phc/staff/patients/search",
        { params: { q } })).data,
    enabled: q.trim().length >= 2,
    staleTime: 15_000,
  });
}

export function useCreateVisit() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: VisitCreate) =>
      (await http.post<Visit>("/phc/staff/visits", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useCreatePrescription() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: PrescriptionCreate) =>
      (await http.post<Prescription>("/phc/staff/prescriptions", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useMyRecords() {
  return useQuery({
    queryKey: keys.records(),
    queryFn: async () => (await http.get<Page<Visit>>("/phc/records")).data,
  });
}

export function useMyPrescriptions() {
  return useQuery({
    queryKey: keys.prescriptions(),
    queryFn: async () =>
      (await http.get<Page<Prescription>>("/phc/records/prescriptions")).data,
  });
}

/** The download endpoint returns PDF bytes, not a JSON record. Buffer and save
 *  it so a refused or throttled download is reported as a toast, not a page
 *  replacement; the drawer itself renders from the already-loaded record data. */
export function useRecordDownload() {
  return useMutation({
    mutationFn: async (id: number) => {
      try {
        const res = await http.get(`/phc/records/download/${id}`, {
          responseType: "blob",
        });
        saveBlob(
          res.data as Blob,
          filenameFromDisposition(
            res.headers["content-disposition"], `phc-record-${id}.pdf`),
        );
      } catch (e) {
        throw await readBlobError(e);
      }
    },
  });
}

// -- Reimbursement -------------------------------------------------------------
export function useCreateClaim() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: ReimbursementClaimCreate) =>
      (await http.post<ReimbursementClaim>("/phc/claims", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useMyClaims() {
  return useQuery({
    queryKey: keys.claims(),
    queryFn: async () =>
      (await http.get<Page<ReimbursementClaim>>("/phc/claims/mine")).data,
  });
}

export function useReviewClaim() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, note }: ClaimTransition & { id: number }) =>
      (await http.post<ReimbursementClaim>(
        `/phc/staff/claims/${id}/review`, { note: note ?? "" })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useVerifyClaim() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, note }: ClaimTransition & { id: number }) =>
      (await http.post<ReimbursementClaim>(
        `/phc/audit/claims/${id}/verify`, { note: note ?? "" })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useSanctionClaim() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, decision, note }: ClaimDecision & { id: number }) =>
      (await http.post<ReimbursementClaim>(
        `/phc/approver/claims/${id}/sanction`,
        { decision, note: note ?? "" })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useProcessPayment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, note }: ClaimTransition & { id: number }) =>
      (await http.post<ReimbursementClaim>(
        `/phc/audit/claims/${id}/payment`, { note: note ?? "" })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Inventory & procurement ---------------------------------------------------
export function useInventoryItems() {
  return useQuery({
    queryKey: keys.inventory(),
    queryFn: async () =>
      (await http.get<Page<InventoryItem>>("/phc/staff/inventory/items")).data,
    staleTime: 30_000,
  });
}

export function useCreateInventoryItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: InventoryItemCreate) =>
      (await http.post<InventoryItem>("/phc/staff/inventory/items", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useAdjustStock() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: StockAdjustmentCreate) =>
      (await http.post<StockAdjustment>("/phc/staff/inventory/adjust", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useCreateRequisition() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: RequisitionCreate) =>
      (await http.post<Requisition>("/phc/staff/requisitions", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useDecideRequisition() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, decision, note }:
      RequisitionDecision & { id: number }) =>
      (await http.post<Requisition>(
        `/phc/approver/requisitions/${id}/decide`,
        { decision, note: note ?? "" })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useFulfillRequisition() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await http.post<Requisition>(
        `/phc/staff/requisitions/${id}/fulfill`, {})).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Ambulance, advisories, reports, audit -------------------------------------
export function useLogAmbulance() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: AmbulanceLogCreate) =>
      (await http.post<AmbulanceLog>("/phc/staff/ambulance", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function usePublishAdvisory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: HealthAdvisoryCreate) =>
      (await http.post<HealthAdvisory>("/phc/staff/advisories", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useAdvisories(enabled = true) {
  return useQuery({
    queryKey: keys.advisories(),
    queryFn: async () =>
      (await http.get<Page<HealthAdvisory>>("/phc/advisories")).data,
    enabled,
    staleTime: 30_000,
  });
}

export function useAdminReport(category: ReportCategory) {
  return useQuery({
    queryKey: keys.report(category),
    queryFn: async () =>
      (await http.get<AdminReport>("/phc/staff/reports",
        { params: { category } })).data,
    staleTime: 60_000,
  });
}

export function useAuditLog(limit = 50) {
  return useQuery({
    queryKey: keys.auditLog(limit),
    queryFn: async () =>
      (await http.get<Page<AuditLog>>("/phc/audit/log",
        { params: { limit } })).data,
    staleTime: 15_000,
  });
}
