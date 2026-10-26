import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  CreateLeaveApplication, LeaveApplication, LeaveType, Page,
} from "./types";

const KEY = "elm";

export function useLeaveTypes() {
  return useQuery({
    queryKey: [KEY, "leave-types"],
    queryFn: async () =>
      (await http.get<{ results: LeaveType[] }>("/elm/leave-types")).data,
    staleTime: 5 * 60_000,
    retry: false,
  });
}

export function useMyLeaveApplications() {
  return useQuery({
    queryKey: [KEY, "applications", "mine"],
    queryFn: async () =>
      (await http.get<Page<LeaveApplication>>("/elm/applications")).data,
    staleTime: 15_000,
    retry: false,
  });
}

export function useCreateLeaveApplication() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: CreateLeaveApplication) =>
      (await http.post<LeaveApplication>("/elm/applications", body)).data,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: [KEY, "applications"] });
    },
  });
}
