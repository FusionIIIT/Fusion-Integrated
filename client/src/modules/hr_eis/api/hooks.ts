/** Data access hooks for the HR EIS module. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { http } from "../../../lib/http";
import type {
  EmployeeProfile,
  WorkExperience,
  CreateExperiencePayload,
} from "./types";

const KEY = "hr_eis";

export const keys = {
  myProfile: () => [KEY, "my-profile"] as const,
  profiles: () => [KEY, "profiles"] as const,
  experiences: () => [KEY, "experiences"] as const,
};

export function useMyProfile() {
  return useQuery({
    queryKey: keys.myProfile(),
    queryFn: async () => {
      const { data } = await http.get<EmployeeProfile>("/hr-eis/profiles/me/");
      return data;
    },
    retry: false,
  });
}

export function useProfiles() {
  return useQuery({
    queryKey: keys.profiles(),
    queryFn: async () => {
      const { data } = await http.get<EmployeeProfile[] | { results: EmployeeProfile[] }>(
        "/hr-eis/profiles/"
      );
      if (Array.isArray(data)) return data;
      return data.results ?? [];
    },
  });
}

export function useWorkExperiences() {
  return useQuery({
    queryKey: keys.experiences(),
    queryFn: async () => {
      const { data } = await http.get<
        WorkExperience[] | { results: WorkExperience[] }
      >("/hr-eis/experiences/");
      if (Array.isArray(data)) return data;
      return data.results ?? [];
    },
  });
}

export function useCreateWorkExperience() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateExperiencePayload) => {
      const { data } = await http.post<WorkExperience>(
        "/hr-eis/experiences/",
        payload
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.myProfile() });
      qc.invalidateQueries({ queryKey: keys.experiences() });
    },
  });
}

export function useDeleteWorkExperience() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await http.delete(`/hr-eis/experiences/${id}/`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.myProfile() });
      qc.invalidateQueries({ queryKey: keys.experiences() });
    },
  });
}
