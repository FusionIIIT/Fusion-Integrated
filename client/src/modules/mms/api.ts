import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { notifications } from "@mantine/notifications";

import { errorMessage, http } from "../../lib/http";

export interface ListResult<T> {
  results: T[];
}

export interface StudentRequest {
  id: number;
  user_id: number;
  kind: "registration" | "deregistration";
  status: string;
  created_at: string;
  effective_at: string | null;
  history: { status: string; at: string; note: string }[];
}

export interface MenuWeek {
  id: number;
  week_start: string;
  entries: { id: number; day: number; meal: string; item: string }[];
}

export interface VacationSurvey {
  id: number;
  title: string;
  vacation_starts_on: string;
  vacation_ends_on: string;
  deadline: string;
}

export interface MmsBill {
  id: number;
  user_id: number;
  year: number;
  month: number;
  daily_rate: string;
  served_days: number;
  total: string;
  status: string;
}

export interface Overview {
  active_roles: ("caretaker" | "warden")[];
  requests: StudentRequest[];
  rebates: { id: number; user_id: number; status: string; reason: string;
    starts_on: string; ends_on: string }[];
  special_food: { id: number; user_id: number; status: string; reason: string;
    requested_for: string; details: string; charge_amount: string | null }[];
  surveys: VacationSurvey[];
  announcements: { id: number; title: string; body: string; published_at: string }[];
  feedback: { id: number; user_id: number; message: string; created_at: string }[];
  enrollment_count: number;
  special_food_auto_rejection_enabled: boolean;
}

export function useMmsData<T>(path: string, enabled = true) {
  return useQuery({
    queryKey: ["mms", path],
    queryFn: async () => (await http.get<T>(`/mms/${path}`)).data,
    enabled,
  });
}

export interface MmsActionInput {
  body?: Record<string, unknown>;
  path?: string;
}

export function useMmsAction(path: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ body = {}, path: override }: MmsActionInput) =>
      (await http.post(`/mms/${override ?? path}`, body)).data,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["mms"] });
      notifications.show({ color: "green", title: "Saved", message: "Your changes were recorded." });
    },
    onError: (error) => notifications.show({
      color: "red", title: "Could not complete the request",
      message: errorMessage(error),
    }),
  });
}
