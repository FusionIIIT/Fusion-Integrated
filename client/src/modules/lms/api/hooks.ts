import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { http } from "../../../lib/http";
import type {
  Announcement, Assignment, CourseMaterial, CourseWorkspace, Grade, Submission,
} from "./types";

const base = (courseId: number) => `/lms/courses/${courseId}`;

export function useCourseWorkspace(courseId: number) {
  return useQuery<CourseWorkspace>({
    queryKey: ["lms", "course", courseId],
    queryFn: async () => (await http.get<CourseWorkspace>(`/lms/courses/${courseId}/`)).data,
  });
}

export function useMaterials(courseId: number) {
  return useQuery<CourseMaterial[]>({
    queryKey: ["lms", "materials", courseId],
    queryFn: async () => (await http.get<{ results: CourseMaterial[] }>(`${base(courseId)}/materials/`)).data.results ?? (await http.get<CourseMaterial[]>(`${base(courseId)}/materials/`)).data,
  });
}

export function useAnnouncements(courseId: number) {
  return useQuery<Announcement[]>({
    queryKey: ["lms", "announcements", courseId],
    queryFn: async () => (await http.get<{ results: Announcement[] }>(`${base(courseId)}/announcements/`)).data.results ?? (await http.get<Announcement[]>(`${base(courseId)}/announcements/`)).data,
  });
}

export function useAssignments(courseId: number) {
  return useQuery<Assignment[]>({
    queryKey: ["lms", "assignments", courseId],
    queryFn: async () => (await http.get<{ results: Assignment[] }>(`${base(courseId)}/assignments/`)).data.results ?? (await http.get<Assignment[]>(`${base(courseId)}/assignments/`)).data,
  });
}

export function useCreateAssignment(courseId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<Assignment>) =>
      (await http.post<Assignment>(`${base(courseId)}/assignments/`, payload)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["lms", "assignments", courseId] }),
  });
}

export function useSubmitAssignment(courseId: number, assignmentId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { submission_type: string; content: string }) =>
      (await http.post<Submission>(`${base(courseId)}/assignments/${assignmentId}/submit/`, payload)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["lms", "assignments", courseId] }),
  });
}

export function useGradeSubmission(courseId: number, assignmentId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ submissionId, points, feedback }: { submissionId: number; points: number; feedback: string }) =>
      (await http.post<Grade>(`${base(courseId)}/assignments/${assignmentId}/submissions/${submissionId}/grade/`, { points, feedback })).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["lms", "assignments", courseId] }),
  });
}