import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { Page, DoctorSchedule, Visit } from "./types";
import { http } from "../../../lib/http";

const QUERY_KEY_PREFIX = "health-center";

export function useDoctorSchedules() {
  return useQuery({
    queryKey: [QUERY_KEY_PREFIX, "schedules"],
    queryFn: async () => (await http.get<Page<DoctorSchedule>>("/phc/schedules")).data,
  });
}

export function useMyVisits() {
  return useQuery({
    queryKey: [QUERY_KEY_PREFIX, "my-visits"],
    queryFn: async () => (await http.get<Page<Visit>>("/phc/records/mine")).data,
  });
}

export function usePatientVisits(patientId: number | null) {
  return useQuery({
    queryKey: [QUERY_KEY_PREFIX, "visits", patientId],
    queryFn: async () => (await http.get<Page<Visit>>("/phc/visits", { params: { patient_id: patientId } })).data,
    enabled: patientId !== null,
  });
}

export function useCreateSchedule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) => (await http.post("/phc/schedules", body)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY_PREFIX, "schedules"] });
    },
  });
}

export function usePublishSchedule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id }: { id: number }) => (await http.post(`/phc/schedules/${id}/publish`)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY_PREFIX, "schedules"] });
    },
  });
}

export function useSetPresence() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, isPresent }: { id: number; isPresent: boolean }) =>
      (await http.post(`/phc/schedules/${id}/presence`, { is_present: isPresent })).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY_PREFIX, "schedules"] });
    },
  });
}

export function useRecordVisit() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) => (await http.post("/phc/visits", body)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY_PREFIX, "my-visits"] });
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY_PREFIX, "visits"] });
    },
  });
}
