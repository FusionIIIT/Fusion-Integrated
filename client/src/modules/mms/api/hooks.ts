/** TanStack Query hooks for the MMS module. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  Announcement,
  AnnouncementCreateInput,
  Deregistration,
  DeregistrationDecisionInput,
  Feedback,
  FeedbackCreateInput,
  MenuItem,
  MenuItemCreateInput,
  MonthlyBill,
  OperationalReport,
  RebateDecisionInput,
  RebateRequest,
  RebateRequestCreateInput,
  Registration,
  RegistrationDecisionInput,
  RegistrationWindow,
  RegistrationWindowCreateInput,
  RoleAssignment,
  RoleAssignmentCreateInput,
  SpecialFoodDecisionInput,
  SpecialFoodFulfillInput,
  SpecialFoodRequest,
  SpecialFoodRequestCreateInput,
  StudentRequestsOverview,
  SupervisoryReport,
  SurveySummary,
  VacationResponse,
  VacationResponseCreateInput,
  VacationSurvey,
  VacationSurveyCreateInput,
} from "./types";

const KEY = "mms";

export const keys = {
  all: [KEY] as const,
  specialFood: () => [KEY, "special-food"] as const,
  specialFoodDetail: (id: number) => [KEY, "special-food", id] as const,
  registrations: () => [KEY, "registrations"] as const,
  registrationWindows: () => [KEY, "registration-windows"] as const,
  deregistrations: () => [KEY, "deregistrations"] as const,
  rebates: () => [KEY, "rebates"] as const,
  menu: () => [KEY, "menu"] as const,
  bills: () => [KEY, "bills"] as const,
  billDetail: (id: number) => [KEY, "bills", id] as const,
  feedback: () => [KEY, "feedback"] as const,
  surveys: () => [KEY, "surveys"] as const,
  surveySummary: () => [KEY, "survey-summary"] as const,
  announcements: () => [KEY, "announcements"] as const,
  announcementHistory: () => [KEY, "announcements", "history"] as const,
  operationalReport: () => [KEY, "reports", "operational"] as const,
  supervisoryReport: () => [KEY, "reports", "supervisory"] as const,
  roles: () => [KEY, "roles"] as const,
  studentOverview: () => [KEY, "student-overview"] as const,
};

function invalidateMms(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: [KEY] });
}

// -- Special Food -------------------------------------------------------------

export function useSpecialFoodRequests() {
  return useQuery({
    queryKey: keys.specialFood(),
    queryFn: async () => (await http.get<SpecialFoodRequest[]>("/mms/special-food-requests/")).data,
  });
}

export function useSubmitSpecialFoodRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: SpecialFoodRequestCreateInput) =>
      (await http.post<SpecialFoodRequest>("/mms/special-food-requests/", data)).data,
    onSuccess: () => invalidateMms(qc),
  });
}

export function useDecideSpecialFoodRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: number; data: SpecialFoodDecisionInput }) =>
      (await http.post<SpecialFoodRequest>(`/mms/special-food-requests/${id}/decision/`, data)).data,
    onSuccess: () => invalidateMms(qc),
  });
}

export function useFulfillSpecialFoodRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: number; data: SpecialFoodFulfillInput }) =>
      (await http.post<SpecialFoodRequest>(`/mms/special-food-requests/${id}/fulfill/`, data)).data,
    onSuccess: () => invalidateMms(qc),
  });
}

// -- Registrations ------------------------------------------------------------

export function useRegistrations() {
  return useQuery({
    queryKey: keys.registrations(),
    queryFn: async () => (await http.get<Registration[]>("/mms/registration-requests/")).data,
  });
}

export function useSubmitRegistration() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => (await http.post<Registration>("/mms/registration-requests/")).data,
    onSuccess: () => invalidateMms(qc),
  });
}

export function useDecideRegistration() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: number; data: RegistrationDecisionInput }) =>
      (await http.post<Registration>(`/mms/registration-requests/${id}/decision/`, data)).data,
    onSuccess: () => invalidateMms(qc),
  });
}

export function useRegistrationWindows() {
  return useQuery({
    queryKey: keys.registrationWindows(),
    queryFn: async () => (await http.get<RegistrationWindow[]>("/mms/registration-window/")).data,
  });
}

export function useOpenRegistrationWindow() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: RegistrationWindowCreateInput) =>
      (await http.post<RegistrationWindow>("/mms/registration-window/", data)).data,
    onSuccess: () => invalidateMms(qc),
  });
}

// -- Deregistrations ----------------------------------------------------------

export function useDeregistrations() {
  return useQuery({
    queryKey: keys.deregistrations(),
    queryFn: async () => (await http.get<Deregistration[]>("/mms/deregistration-requests/")).data,
  });
}

export function useSubmitDeregistration() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => (await http.post<Deregistration>("/mms/deregistration-requests/")).data,
    onSuccess: () => invalidateMms(qc),
  });
}

export function useDecideDeregistration() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: number; data: DeregistrationDecisionInput }) =>
      (await http.post<Deregistration>(`/mms/deregistration-requests/${id}/decision/`, data)).data,
    onSuccess: () => invalidateMms(qc),
  });
}

// -- Rebates ------------------------------------------------------------------

export function useRebates() {
  return useQuery({
    queryKey: keys.rebates(),
    queryFn: async () => (await http.get<RebateRequest[]>("/mms/rebate-requests/")).data,
  });
}

export function useSubmitRebate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: RebateRequestCreateInput) =>
      (await http.post<RebateRequest>("/mms/rebate-requests/", data)).data,
    onSuccess: () => invalidateMms(qc),
  });
}

export function useDecideRebate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: number; data: RebateDecisionInput }) =>
      (await http.post<RebateRequest>(`/mms/rebate-requests/${id}/decision/`, data)).data,
    onSuccess: () => invalidateMms(qc),
  });
}

// -- Menu ---------------------------------------------------------------------

export function useMenuItems() {
  return useQuery({
    queryKey: keys.menu(),
    queryFn: async () => (await http.get<MenuItem[]>("/mms/menu/")).data,
  });
}

export function useUpsertMenuItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: MenuItemCreateInput) =>
      (await http.post<MenuItem>("/mms/menu/items/", data)).data,
    onSuccess: () => invalidateMms(qc),
  });
}

export function useDeleteMenuItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await http.delete(`/mms/menu/items/?id=${id}`);
    },
    onSuccess: () => invalidateMms(qc),
  });
}

// -- Billing ------------------------------------------------------------------

export function useMonthlyBills() {
  return useQuery({
    queryKey: keys.bills(),
    queryFn: async () => (await http.get<MonthlyBill[]>("/mms/bills/")).data,
  });
}

export function useGenerateMonthlyBills() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => (await http.post<{ generated_count: number }>("/mms/bills/generate/")).data,
    onSuccess: () => invalidateMms(qc),
  });
}

export function useFinalizeBill() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await http.post<MonthlyBill>(`/mms/bills/${id}/finalize/`)).data,
    onSuccess: () => invalidateMms(qc),
  });
}

export function usePublishBill() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await http.post<MonthlyBill>(`/mms/bills/${id}/publish/`)).data,
    onSuccess: () => invalidateMms(qc),
  });
}

// -- Feedback -----------------------------------------------------------------

export function useFeedback() {
  return useQuery({
    queryKey: keys.feedback(),
    queryFn: async () => (await http.get<Feedback[]>("/mms/feedback/")).data,
  });
}

export function useSubmitFeedback() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: FeedbackCreateInput) =>
      (await http.post<Feedback>("/mms/feedback/", data)).data,
    onSuccess: () => invalidateMms(qc),
  });
}

// -- Vacation Surveys ---------------------------------------------------------

export function useVacationSurveys() {
  return useQuery({
    queryKey: keys.surveys(),
    queryFn: async () => (await http.get<VacationSurvey[]>("/mms/surveys/")).data,
  });
}

export function useCreateVacationSurvey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: VacationSurveyCreateInput) =>
      (await http.post<VacationSurvey>("/mms/surveys/", data)).data,
    onSuccess: () => invalidateMms(qc),
  });
}

export function useRespondVacationSurvey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ surveyId, data }: { surveyId: number; data: VacationResponseCreateInput }) =>
      (await http.post<VacationResponse>(`/mms/surveys/${surveyId}/respond/`, data)).data,
    onSuccess: () => invalidateMms(qc),
  });
}

export function useVacationSurveySummary() {
  return useQuery({
    queryKey: keys.surveySummary(),
    queryFn: async () => (await http.get<SurveySummary[]>("/mms/survey-summary/")).data,
  });
}

// -- Announcements ------------------------------------------------------------

export function useAnnouncements() {
  return useQuery({
    queryKey: keys.announcements(),
    queryFn: async () => (await http.get<Announcement[]>("/mms/announcements/")).data,
  });
}

export function useAnnouncementHistory() {
  return useQuery({
    queryKey: keys.announcementHistory(),
    queryFn: async () => (await http.get<Announcement[]>("/mms/announcements/history/")).data,
  });
}

export function usePublishAnnouncement() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: AnnouncementCreateInput) =>
      (await http.post<Announcement>("/mms/announcements/", data)).data,
    onSuccess: () => invalidateMms(qc),
  });
}

// -- Reports ------------------------------------------------------------------

export function useOperationalReport() {
  return useQuery({
    queryKey: keys.operationalReport(),
    queryFn: async () => (await http.get<OperationalReport>("/mms/reports/operational/")).data,
  });
}

export function useSupervisoryReport() {
  return useQuery({
    queryKey: keys.supervisoryReport(),
    queryFn: async () => (await http.get<SupervisoryReport>("/mms/reports/supervisory/")).data,
  });
}

// -- Roles (Mess Admin) -------------------------------------------------------

export function useRoleAssignments() {
  return useQuery({
    queryKey: keys.roles(),
    queryFn: async () => (await http.get<RoleAssignment[]>("/mms/roles/")).data,
  });
}

export function useAssignRole() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: RoleAssignmentCreateInput) =>
      (await http.post<RoleAssignment>("/mms/roles/", data)).data,
    onSuccess: () => invalidateMms(qc),
  });
}

// -- Unified Student Requests Overview ----------------------------------------

export function useStudentRequestsOverview() {
  return useQuery({
    queryKey: keys.studentOverview(),
    queryFn: async () => (await http.get<StudentRequestsOverview>("/mms/requests/")).data,
  });
}
