// One TanStack Query hook per PHC endpoint; every mutation invalidates the whole module.
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { filenameFromDisposition, saveBlob } from "../../../lib/download";
import { http, readBlobError } from "../../../lib/http";
import type {
  Advisory, AmbulanceInput, AmbulanceLog, Claim, ClaimInput, EligiblePrescription,
  InventoryItem, InventoryItemInput, LowStockAlert, Notification, Page, Patient, Report,
  ReportCategory, Requisition, RequisitionInput, Schedule, ScheduleInput,
  StockAdjustment, Visit, VisitInput,
} from "./types";

const KEY = "phc";

function useInvalidate() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: [KEY] });
}

function useList<T>(name: string, path: string, params?: object) {
  return useQuery({
    queryKey: [KEY, name, params],
    queryFn: async () => (await http.get<T>(path, { params })).data,
  });
}

function useWrite<TIn, TOut>(send: (input: TIn) => Promise<TOut>) {
  const invalidate = useInvalidate();
  return useMutation({ mutationFn: send, onSuccess: invalidate });
}

// -- Schedules ---------------------------------------------------------------------
export const useSchedules = () => useList<Schedule[]>("schedules", "/phc/schedules");

export const useCreateSchedule = () => useWrite(async (input: ScheduleInput) =>
  (await http.post<Schedule>("/phc/schedules", input)).data);

export const useUpdateSchedule = () => useWrite(
  async ({ id, ...input }: ScheduleInput & { id: number }) =>
    (await http.put<Schedule>(`/phc/schedules/${id}`, input)).data);

export const usePublishSchedule = () => useWrite(async (id: number) =>
  (await http.post<Schedule>(`/phc/schedules/${id}/publish`)).data);

export const useMarkAttendance = () => useWrite(
  async ({ id, status }: { id: number; status: "available" | "departed" }) =>
    (await http.post(`/phc/schedules/${id}/attendance`, { status })).data);

// -- Records -----------------------------------------------------------------------
export const useVisits = () => useList<Page<Visit>>("visits", "/phc/records");

export function usePatientSearch(q: string) {
  return useQuery({
    queryKey: [KEY, "patients", q],
    queryFn: async () => (await http.get<Patient[]>("/phc/patients", { params: { q } })).data,
    enabled: q.trim().length >= 2,
  });
}

export const useRecordVisit = () => useWrite(async (input: VisitInput) =>
  (await http.post<Visit>("/phc/records", input)).data);

export function useDownloadRecords() {
  return useMutation({
    mutationFn: async (ids: number[]) => {
      try {
        const res = await http.get("/phc/records/pdf", {
          params: { ids: ids.join(",") }, responseType: "blob",
        });
        saveBlob(res.data, filenameFromDisposition(
          res.headers["content-disposition"], "phc-medical-records.pdf"));
      } catch (e) {
        throw await readBlobError(e);
      }
    },
  });
}

// -- Claims ------------------------------------------------------------------------
export const useClaims = () => useList<Page<Claim>>("claims", "/phc/claims");

export function useEligiblePrescriptions(enabled: boolean) {
  return useQuery({
    queryKey: [KEY, "eligible-prescriptions"],
    queryFn: async () =>
      (await http.get<EligiblePrescription[]>("/phc/claims/prescriptions")).data,
    enabled,
  });
}

export const useSubmitClaim = () => useWrite(async (input: ClaimInput) =>
  (await http.post<Claim>("/phc/claims", input)).data);

export const useClaimTransition = () => useWrite(
  async ({ id, event, note }: { id: number; event: string; note: string }) =>
    (await http.post<Claim>(`/phc/claims/${id}/transition`, { event, note })).data);

// -- Inventory ---------------------------------------------------------------------
export const useInventory = () => useList<Page<InventoryItem>>("inventory", "/phc/inventory");

export const useLowStockAlerts = () =>
  useList<Page<LowStockAlert>>("alerts", "/phc/inventory/alerts");

export const useCreateItem = () => useWrite(async (input: InventoryItemInput) =>
  (await http.post<InventoryItem>("/phc/inventory", input)).data);

export const useAdjustStock = () => useWrite(
  async ({ id, delta, reason }: { id: number; delta: string; reason: string }) =>
    (await http.post<StockAdjustment>(`/phc/inventory/${id}/adjust`, { delta, reason })).data);

// -- Requisitions ------------------------------------------------------------------
export const useRequisitions = () =>
  useList<Page<Requisition>>("requisitions", "/phc/requisitions");

export const useSubmitRequisition = () => useWrite(async (input: RequisitionInput) =>
  (await http.post<Requisition>("/phc/requisitions", input)).data);

export const useRequisitionTransition = () => useWrite(
  async ({ id, event, note }: { id: number; event: string; note: string }) =>
    (await http.post<Requisition>(`/phc/requisitions/${id}/transition`, { event, note })).data);

// -- Ambulance, advisories, reports, notifications --------------------------------
export const useAmbulanceLogs = () => useList<Page<AmbulanceLog>>("ambulance", "/phc/ambulance");

export const useLogAmbulance = () => useWrite(async (input: AmbulanceInput) =>
  (await http.post<AmbulanceLog>("/phc/ambulance", input)).data);

export const useAdvisories = () => useList<Page<Advisory>>("advisories", "/phc/advisories");

export const usePublishAdvisory = () => useWrite(
  async (input: { title: string; body: string }) =>
    (await http.post<Advisory>("/phc/advisories", input)).data);

export function useReport(params: { category: ReportCategory; start: string; end: string } | null) {
  return useQuery({
    queryKey: [KEY, "report", params],
    queryFn: async () => (await http.get<Report>("/phc/reports", { params })).data,
    enabled: params !== null,
  });
}

export const useNotifications = () =>
  useList<Page<Notification>>("notifications", "/phc/notifications");
