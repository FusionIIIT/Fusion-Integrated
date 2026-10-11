import { useMutation, useQuery } from "@tanstack/react-query";
import { notifications } from "@mantine/notifications";

import { http } from "../../../lib/http";
import type { LeaveRequest } from "./types";

type Page<T> = { results: T[]; count?: number };
type Application = LeaveRequest;

export function useLeaveRequests() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["elm", "leave-requests"],
    queryFn: async () =>
      (await http.get<Page<LeaveRequest>>("/elm/leaves")).data,
    staleTime: 30_000,
  });

  return {
    data,
    isPending: isLoading,
    error,
  };
}

export function useTransition() {
  const { mutate, isLoading } = useMutation({
    mutationFn: async (body) =>
      (await http.post<LeaveRequest>(`/elm/leaves/${body.id}/transition`, body)).data,
    onSuccess: () => notifications.show({ color: "green", title: "Transitioned" }),
  });

  return {
    mutate,
    isPending: isLoading,
  };
}

export function useApplications() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["elm", "applications"],
    queryFn: async () =>
      (await http.get<Page<Application>>("/elm/applications")).data,
    staleTime: 30_000,
  });

  return {
    data,
    isPending: isLoading,
    error,
  };
}

export function useSubmitLeaveRequest() {
  const { mutate, isLoading } = useMutation({
    mutationFn: async (body) =>
      (await http.post<LeaveRequest>("/elm/leaves/create", body)).data,
    onSuccess: () => notifications.show({ color: "green", title: "Submitted" }),
  });

  return {
    mutate,
    isPending: isLoading,
  };
}
