import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { http } from "../../../lib/http";
import type {
  DepartmentAnnouncement,
  GraduateSeminar,
  Page,
  ScheduleSeminarInput,
  SeminarRequest,
  SubmitSeminarRequestInput,
  TAAllocation,
  ThesisSupervisorAllocation,
} from "./types";

const KEY = "department";

export const keys = {
  all: [KEY] as const,
  requests: () => [KEY, "requests"] as const,
  pending: () => [KEY, "pending"] as const,
  seminars: () => [KEY, "seminars"] as const,
  taAllocations: () => [KEY, "allocations", "ta"] as const,
  supervisorAllocations: () => [KEY, "allocations", "supervisors"] as const,
  announcements: () => [KEY, "announcements"] as const,
};

function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: [KEY] });
}

// -- Seminar Requests (OA-UC-51) ---------------------------------------------

export function useSeminarRequests() {
  return useQuery({
    queryKey: keys.requests(),
    queryFn: async () => {
      const res = (await http.get<Page<SeminarRequest> | SeminarRequest[]>("/department/requests/")).data;
      return Array.isArray(res) ? res : res.results;
    },
  });
}

export function usePendingSeminars() {
  return useQuery({
    queryKey: keys.pending(),
    queryFn: async () => {
      const res = (await http.get<Page<SeminarRequest> | SeminarRequest[]>("/department/pending/")).data;
      return Array.isArray(res) ? res : res.results;
    },
  });
}

export function useScheduledSeminars(department: string = "") {
  return useQuery({
    queryKey: [...keys.seminars(), department],
    queryFn: async () => {
      const url = department
        ? `/department/seminars/?department=${encodeURIComponent(department)}`
        : "/department/seminars/";
      const res = (await http.get<Page<GraduateSeminar> | GraduateSeminar[]>(url)).data;
      return Array.isArray(res) ? res : res.results;
    },
  });
}

export function useSubmitSeminarRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: SubmitSeminarRequestInput) =>
      (await http.post<SeminarRequest>("/department/requests/", data)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useScheduleSeminar() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: number; data: ScheduleSeminarInput }) =>
      (await http.post<GraduateSeminar>(`/department/requests/${id}/schedule/`, data)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useRejectSeminar() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, reason }: { id: number; reason: string }) =>
      (await http.post<SeminarRequest>(`/department/requests/${id}/reject/`, { reason })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useCancelSeminar() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await http.delete<SeminarRequest>(`/department/requests/${id}/`)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Allocations (AFR-OAP-043, AFR-OAP-044) -----------------------------------

export function useTAAllocations() {
  return useQuery({
    queryKey: keys.taAllocations(),
    queryFn: async () => {
      const res = (await http.get<Page<TAAllocation> | TAAllocation[]>("/department/allocations/ta/")).data;
      return Array.isArray(res) ? res : res.results;
    },
  });
}

export function useCreateTAAllocation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: Partial<TAAllocation>) =>
      (await http.post<TAAllocation>("/department/allocations/ta/", data)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useSupervisorAllocations() {
  return useQuery({
    queryKey: keys.supervisorAllocations(),
    queryFn: async () => {
      const res = (await http.get<Page<ThesisSupervisorAllocation> | ThesisSupervisorAllocation[]>(
        "/department/allocations/supervisors/"
      )).data;
      return Array.isArray(res) ? res : res.results;
    },
  });
}

export function useCreateSupervisorAllocation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: Partial<ThesisSupervisorAllocation>) =>
      (await http.post<ThesisSupervisorAllocation>("/department/allocations/supervisors/", data)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Announcements ------------------------------------------------------------

export function useAnnouncements() {
  return useQuery({
    queryKey: keys.announcements(),
    queryFn: async () => {
      const res = (await http.get<Page<DepartmentAnnouncement> | DepartmentAnnouncement[]>(
        "/department/announcements/"
      )).data;
      return Array.isArray(res) ? res : res.results;
    },
  });
}

export function useCreateAnnouncement() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: Partial<DepartmentAnnouncement>) =>
      (await http.post<DepartmentAnnouncement>("/department/announcements/", data)).data,
    onSuccess: () => invalidateAll(qc),
  });
}
