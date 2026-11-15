import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  Application,
  CatalogueVersion,
  SaveDraftRequest,
  StartApplicationRequest,
} from "./types";

const KEY = "spacs";

export const keys = {
  catalogue: () => [KEY, "catalogue"] as const,
  applications: () => [KEY, "applications"] as const,
};

function invalidateSpacs(queryClient: ReturnType<typeof useQueryClient>) {
  return queryClient.invalidateQueries({ queryKey: [KEY] });
}

export function useCatalogue() {
  return useQuery({
    queryKey: keys.catalogue(),
    queryFn: async () =>
      (await http.get<CatalogueVersion[]>("/spacs/catalogue")).data,
  });
}

export function useApplications() {
  return useQuery({
    queryKey: keys.applications(),
    queryFn: async () =>
      (await http.get<Application[]>("/spacs/applications")).data,
  });
}

export function useCreateApplication() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: StartApplicationRequest) =>
      (await http.post<Application>("/spacs/applications", body)).data,
    onSuccess: () => invalidateSpacs(queryClient),
  });
}

export function useSaveDraft() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ public_id, application_data }: SaveDraftRequest) =>
      (await http.patch<Application>(`/spacs/applications/${public_id}`, {
        application_data,
      })).data,
    onSuccess: () => invalidateSpacs(queryClient),
  });
}

export function useSubmitApplication() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (publicId: string) =>
      (await http.post<Application>(
        `/spacs/applications/${publicId}/submit`,
        {},
      )).data,
    onSuccess: () => invalidateSpacs(queryClient),
  });
}

export function useResubmitApplication() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (publicId: string) =>
      (await http.post<Application>(
        `/spacs/applications/${publicId}/resubmit`,
        {},
      )).data,
    onSuccess: () => invalidateSpacs(queryClient),
  });
}
