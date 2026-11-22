import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { http } from "../../../lib/http";
import type {
  AmbulanceLog,
  Doctor,
  DoctorAvailability,
  DoctorScheduleItem,
  HealthAnnouncement,
  InventoryItem,
  PatientVisit,
  PHCAuditTrail,
  PHCNotification,
  Prescription,
  ProcurementRequisition,
  ReimbursementClaim,
  StockAdjustment,
} from "./types";

const KEY = "phc";

export const keys = {
  availability: () => [KEY, "availability"] as const,
  doctors: () => [KEY, "doctors"] as const,
  schedules: () => [KEY, "schedules"] as const,
  attendance: () => [KEY, "attendance"] as const,
  myHistory: () => [KEY, "my-history"] as const,
  myPrescriptions: () => [KEY, "my-prescriptions"] as const,
  staffVisits: (q?: string) => [KEY, "staff-visits", q] as const,
  myClaims: () => [KEY, "my-claims"] as const,
  claimQueue: (stage?: string) => [KEY, "claim-queue", stage] as const,
  claimDetail: (id: number) => [KEY, "claim-detail", id] as const,
  inventory: (cat?: string) => [KEY, "inventory", cat] as const,
  adjustments: (itemId?: number) => [KEY, "adjustments", itemId] as const,
  requisitions: (status?: string) => [KEY, "requisitions", status] as const,
  ambulance: () => [KEY, "ambulance"] as const,
  announcements: () => [KEY, "announcements"] as const,
  reports: (type: string) => [KEY, "reports", type] as const,
  audit: (type?: string) => [KEY, "audit", type] as const,
  notifications: () => [KEY, "notifications"] as const,
};

function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: [KEY] });
}

// --- Doctor Availability & Schedules ---
export function useDoctorAvailability() {
  return useQuery({
    queryKey: keys.availability(),
    queryFn: async () => {
      const res = await http.get<DoctorAvailability[]>("/phc/doctors/availability/");
      return res.data;
    },
  });
}

export function useDoctors() {
  return useQuery({
    queryKey: keys.doctors(),
    queryFn: async () => {
      const res = await http.get<Doctor[]>("/phc/doctors/");
      return res.data;
    },
  });
}

export function useCreateDoctor() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<Doctor>) => {
      const res = await http.post<Doctor>("/phc/doctors/", payload);
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useDoctorSchedules() {
  return useQuery({
    queryKey: keys.schedules(),
    queryFn: async () => {
      const res = await http.get<DoctorScheduleItem[]>("/phc/doctors/schedules/");
      return res.data;
    },
  });
}

export function useSaveDoctorSchedule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      doctor_id: number;
      day_of_week: string;
      start_time: string;
      end_time: string;
      room_number?: string;
      is_published?: boolean;
      schedule_id?: number;
    }) => {
      const res = await http.post("/phc/doctors/schedules/", payload);
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function usePublishSchedules() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (schedule_ids: number[]) => {
      const res = await http.post("/phc/doctors/schedules/publish/", { schedule_ids });
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useDoctorAttendance() {
  return useQuery({
    queryKey: keys.attendance(),
    queryFn: async () => {
      const res = await http.get("/phc/doctors/attendance/");
      return res.data;
    },
  });
}

export function useMarkDoctorAttendance() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { doctor_id: number; status: string; remarks?: string }) => {
      const res = await http.post("/phc/doctors/attendance/", payload);
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

// --- Patient Clinical Records ---
export function useMyMedicalHistory() {
  return useQuery({
    queryKey: keys.myHistory(),
    queryFn: async () => {
      const res = await http.get<PatientVisit[]>("/phc/patient/history/");
      return res.data;
    },
  });
}

export function useMyPrescriptions() {
  return useQuery({
    queryKey: keys.myPrescriptions(),
    queryFn: async () => {
      const res = await http.get<Prescription[]>("/phc/patient/prescriptions/");
      return res.data;
    },
  });
}

export function useStaffPatientVisits(q?: string) {
  return useQuery({
    queryKey: keys.staffVisits(q),
    queryFn: async () => {
      const res = await http.get<PatientVisit[]>("/phc/staff/visits/", { params: { q } });
      return res.data;
    },
  });
}

export function useCreatePatientVisit() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      patient_user_id: number;
      doctor_id?: number | null;
      visit_date?: string;
      symptoms: string;
      diagnosis: string;
      notes?: string;
    }) => {
      const res = await http.post<PatientVisit>("/phc/staff/visits/", payload);
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useCreatePrescription() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      visit_id: number;
      prescription_number: string;
      medicines_prescribed: string;
      prescribed_date?: string;
      scanned_document_url?: string;
      notes?: string;
    }) => {
      const res = await http.post<Prescription>("/phc/staff/prescriptions/", payload);
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

// --- Reimbursements ---
export function useMyReimbursements() {
  return useQuery({
    queryKey: keys.myClaims(),
    queryFn: async () => {
      const res = await http.get<ReimbursementClaim[]>("/phc/reimbursements/mine/");
      return res.data;
    },
  });
}

export function useReimbursementReviewQueue(stage?: string) {
  return useQuery({
    queryKey: keys.claimQueue(stage),
    queryFn: async () => {
      const res = await http.get<ReimbursementClaim[]>("/phc/reimbursements/queue/", { params: { stage } });
      return res.data;
    },
  });
}

export function useReimbursementClaimDetail(id: number) {
  return useQuery({
    queryKey: keys.claimDetail(id),
    queryFn: async () => {
      const res = await http.get<ReimbursementClaim>(`/phc/reimbursements/${id}/`);
      return res.data;
    },
    enabled: Boolean(id),
  });
}

export function useSubmitReimbursement() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      prescription_id: number;
      expense_date: string;
      amount_claimed: number;
      bills_document_url?: string;
      remarks?: string;
    }) => {
      const res = await http.post<ReimbursementClaim>("/phc/reimbursements/submit/", payload);
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useForwardClaimPHC() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ claimId, comments }: { claimId: number; comments?: string }) => {
      const res = await http.post(`/phc/reimbursements/${claimId}/forward/`, { comments });
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useVerifyClaimAccounts() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ claimId, amountVerified, comments }: { claimId: number; amountVerified?: number; comments?: string }) => {
      const res = await http.post(`/phc/reimbursements/${claimId}/verify/`, {
        amount_verified: amountVerified,
        comments,
      });
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useSanctionClaim() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      claimId,
      decision,
      sanctionedAmount,
      comments,
    }: {
      claimId: number;
      decision: "approve" | "reject";
      sanctionedAmount?: number;
      comments?: string;
    }) => {
      const res = await http.post(`/phc/reimbursements/${claimId}/sanction/`, {
        decision,
        sanctioned_amount: sanctionedAmount,
        comments,
      });
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useProcessClaimPayment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ claimId, paymentReference, comments }: { claimId: number; paymentReference?: string; comments?: string }) => {
      const res = await http.post(`/phc/reimbursements/${claimId}/pay/`, {
        payment_reference: paymentReference,
        comments,
      });
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

// --- Inventory & Requisitions ---
export function useInventoryItems(category?: string) {
  return useQuery({
    queryKey: keys.inventory(category),
    queryFn: async () => {
      const res = await http.get<InventoryItem[]>("/phc/inventory/items/", { params: { category } });
      return res.data;
    },
  });
}

export function useSaveInventoryItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<InventoryItem> & { item_id?: number }) => {
      const res = await http.post<InventoryItem>("/phc/inventory/items/", payload);
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useAdjustStock() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { item_id: number; adjustment_type: "ADD" | "DEDUCT"; quantity: number; reason: string }) => {
      const res = await http.post<InventoryItem>("/phc/inventory/adjust/", payload);
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useStockAdjustments(itemId?: number) {
  return useQuery({
    queryKey: keys.adjustments(itemId),
    queryFn: async () => {
      const res = await http.get<StockAdjustment[]>("/phc/inventory/adjust/", { params: { item_id: itemId } });
      return res.data;
    },
  });
}

export function useProcurementRequisitions(status?: string) {
  return useQuery({
    queryKey: keys.requisitions(status),
    queryFn: async () => {
      const res = await http.get<ProcurementRequisition[]>("/phc/inventory/requisitions/", { params: { status } });
      return res.data;
    },
  });
}

export function useSubmitRequisition() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { justification: string; items: { item_id: number; quantity: number }[] }) => {
      const res = await http.post<ProcurementRequisition>("/phc/inventory/requisitions/", payload);
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useDecideRequisition() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ reqId, decision, remarks }: { reqId: number; decision: "approve" | "reject"; remarks?: string }) => {
      const res = await http.post(`/phc/inventory/requisitions/${reqId}/decide/`, { decision, remarks });
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useFulfillRequisition() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (reqId: number) => {
      const res = await http.post(`/phc/inventory/requisitions/${reqId}/fulfill/`);
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

// --- Ambulance, Announcements, Reports, Audit, Notifications ---
export function useAmbulanceLogs() {
  return useQuery({
    queryKey: keys.ambulance(),
    queryFn: async () => {
      const res = await http.get<AmbulanceLog[]>("/phc/ambulance/");
      return res.data;
    },
  });
}

export function useLogAmbulance() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<AmbulanceLog>) => {
      const res = await http.post<AmbulanceLog>("/phc/ambulance/", payload);
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useHealthAnnouncements() {
  return useQuery({
    queryKey: keys.announcements(),
    queryFn: async () => {
      const res = await http.get<HealthAnnouncement[]>("/phc/announcements/");
      return res.data;
    },
  });
}

export function usePublishAnnouncement() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { title: string; content: string; priority: string }) => {
      const res = await http.post<HealthAnnouncement>("/phc/announcements/", payload);
      return res.data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function usePHCReport(reportType: string) {
  return useQuery({
    queryKey: keys.reports(reportType),
    queryFn: async () => {
      const res = await http.get<any>("/phc/reports/", { params: { type: reportType } });
      return res.data;
    },
  });
}

export function usePHCAuditTrail(targetType?: string) {
  return useQuery({
    queryKey: keys.audit(targetType),
    queryFn: async () => {
      const res = await http.get<PHCAuditTrail[]>("/phc/audit/", { params: { target_type: targetType } });
      return res.data;
    },
  });
}

export function usePHCNotifications() {
  return useQuery({
    queryKey: keys.notifications(),
    queryFn: async () => {
      const res = await http.get<{ unread_count: number; notifications: PHCNotification[] }>("/phc/notifications/");
      return res.data;
    },
  });
}
