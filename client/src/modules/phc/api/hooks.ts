import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { filenameFromDisposition, saveBlob } from "../../../lib/download";
import { http, readBlobError } from "../../../lib/http";
import type {
  AmbulanceUsage, Attendance, HealthAdvisory, InventoryItem, Notification,
  Page, PatientSearchResult, PatientVisit, ReimbursementClaim, Report, Requisition,
  ScheduleSlot,
} from "./types";

const ROOT = "/phc";
const keys = {
  availability: ["phc", "availability"] as const,
  records: ["phc", "records"] as const,
  claims: ["phc", "claims"] as const,
  schedules: ["phc", "schedules"] as const,
  attendance: ["phc", "attendance"] as const,
  inventory: ["phc", "inventory"] as const,
  alerts: ["phc", "alerts"] as const,
  requisitions: ["phc", "requisitions"] as const,
  ambulance: ["phc", "ambulance"] as const,
  advisories: ["phc", "advisories"] as const,
  notifications: ["phc", "notifications"] as const,
  reports: ["phc", "reports"] as const,
};

function usePage<T>(key: readonly string[], path: string) {
  return useQuery({
    queryKey: key,
    queryFn: async () => (await http.get<Page<T>>(`${ROOT}${path}`)).data,
  });
}

function useList<T>(key: readonly string[], path: string) {
  return useQuery({
    queryKey: key,
    queryFn: async () => (await http.get<T[]>(`${ROOT}${path}`)).data,
  });
}

function useRefresh() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: ["phc"] });
}

export function useDoctorAvailability() {
  return useList<ScheduleSlot>(keys.availability, "/doctor-availability");
}

export function usePatientRecords() {
  return usePage<PatientVisit>(keys.records, "/records");
}

export function useExportMedicalPdf() {
  return useMutation({
    mutationFn: async (visitIds: number[]) => {
      try {
        const response = await http.post<Blob>(`${ROOT}/records/pdf`,
          { visit_ids: visitIds }, { responseType: "blob" });
        saveBlob(response.data, filenameFromDisposition(
          response.headers["content-disposition"], "medical-records.pdf"));
      } catch (error) {
        throw await readBlobError(error);
      }
    },
  });
}

export function useReimbursementClaims() {
  return usePage<ReimbursementClaim>(keys.claims, "/reimbursements");
}

export function useDoctorSchedules() {
  return usePage<ScheduleSlot>(keys.schedules, "/doctor-schedules");
}

export function useDoctorAttendance() {
  return usePage<Attendance>(keys.attendance, "/doctor-attendance");
}

export function useInventory() {
  return usePage<InventoryItem>(keys.inventory, "/inventory");
}

export function useLowStockAlerts() {
  return usePage<{ id: number; item_name: string; quantity_after: number;
    reorder_threshold: number }>(keys.alerts, "/inventory/low-stock-alerts");
}

export function useRequisitions() {
  return usePage<Requisition>(keys.requisitions, "/requisitions");
}

export function useAmbulanceUsage() {
  return usePage<AmbulanceUsage>(keys.ambulance, "/ambulance-usage");
}

export function useAdvisories() {
  return usePage<HealthAdvisory>(keys.advisories, "/advisories");
}

export function useNotifications() {
  return usePage<Notification>(keys.notifications, "/notifications");
}

export function useReport(reportType: string) {
  return useQuery({
    queryKey: [...keys.reports, reportType],
    queryFn: async () => (await http.get<Report>(`${ROOT}/reports/${reportType}`)).data,
  });
}

export function useCreateVisit() {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: async (body: {
      patient_user_id: number; visited_on: string; notes: string;
      prescription_details: string; issued_on: string;
    }) => (await http.post<PatientVisit>(`${ROOT}/visits`, body)).data,
    onSuccess: refresh,
  });
}

export function usePatientSearch(query: string) {
  return useQuery({
    queryKey: ["phc", "patient-search", query],
    queryFn: async () => (await http.get<PatientSearchResult[]>(
      `${ROOT}/directory/patients`, { params: { q: query } })).data,
    enabled: query.trim().length >= 2,
  });
}

export function useSubmitClaim() {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: async (body: {
      prescription_id: number; claim_amount: string; expense_date: string;
      bill_reference?: string; remarks?: string;
    }) => (await http.post<ReimbursementClaim>(`${ROOT}/reimbursements`, body)).data,
    onSuccess: refresh,
  });
}

export function useTransitionClaim(event: "review" | "verification" | "sanction" | "payment") {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: async ({ id, decision }: { id: number; decision?: "approve" | "reject" }) => {
      const path = event === "sanction" ? `${ROOT}/reimbursements/${id}/sanction` :
        `${ROOT}/reimbursements/${id}/${event}`;
      const body = event === "sanction" ? { decision } : {};
      return (await http.post<ReimbursementClaim>(path, body)).data;
    },
    onSuccess: refresh,
  });
}

export function useCreateSchedule() {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: async (body: {
      doctor_id?: number; display_name?: string; specialization?: string;
      day_of_week: number; starts_at: string; ends_at: string;
    }) => (await http.post<ScheduleSlot>(`${ROOT}/doctor-schedules`, body)).data,
    onSuccess: refresh,
  });
}

export function usePublishSchedule() {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: async (id: number) =>
      (await http.post<ScheduleSlot>(`${ROOT}/doctor-schedules/${id}/publish`, {})).data,
    onSuccess: refresh,
  });
}

export function useSetAttendance() {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: async (body: { doctor_id: number; status: "available" | "departed" }) =>
      (await http.post<Attendance>(`${ROOT}/doctor-attendance`, body)).data,
    onSuccess: refresh,
  });
}

export function useCreateInventoryItem() {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: async (body: { name: string; unit: string; reorder_threshold: number }) =>
      (await http.post<InventoryItem>(`${ROOT}/inventory`, body)).data,
    onSuccess: refresh,
  });
}

export function useAdjustStock() {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: async ({ id, quantity_delta, reason }: {
      id: number; quantity_delta: number; reason: string;
    }) => (await http.post(`${ROOT}/inventory/${id}/movements`, {
      quantity_delta, reason,
    })).data,
    onSuccess: refresh,
  });
}

export function useRecordAmbulanceUsage() {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: async (body: { used_at: string; patient_name: string;
      destination: string }) =>
      (await http.post<AmbulanceUsage>(`${ROOT}/ambulance-usage`, body)).data,
    onSuccess: refresh,
  });
}

export function usePublishAdvisory() {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: async (body: { title: string; body: string }) =>
      (await http.post<HealthAdvisory>(`${ROOT}/advisories`, body)).data,
    onSuccess: refresh,
  });
}

export function useSubmitRequisition() {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: async (body: { lines: Array<{ item_id: number; quantity: number }> }) =>
      (await http.post<Requisition>(`${ROOT}/requisitions`, body)).data,
    onSuccess: refresh,
  });
}

export function useRequisitionDecision() {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: async ({ id, decision }: { id: number; decision: "approve" | "reject" }) =>
      (await http.post<Requisition>(`${ROOT}/requisitions/${id}/decision`, { decision })).data,
    onSuccess: refresh,
  });
}

export function useFulfillRequisition() {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: async (id: number) =>
      (await http.post<Requisition>(`${ROOT}/requisitions/${id}/fulfill`, {})).data,
    onSuccess: refresh,
  });
}
