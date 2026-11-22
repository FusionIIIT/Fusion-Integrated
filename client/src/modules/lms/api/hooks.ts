import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { http } from "../../../lib/http";
import type {
  Assignment,
  CourseAnnouncement,
  CourseMaterial,
  CourseMembership,
  CourseWorkspace,
  Grade,
  StudentSubmission,
} from "./types";

export function useUserCourses() {
  return useQuery({
    queryKey: ["lms", "courses"],
    queryFn: async () => {
      const res = await http.get<CourseMembership[]>("/lms/courses/");
      return res.data;
    },
  });
}

export function useCourseDetail(courseId: number) {
  return useQuery({
    queryKey: ["lms", "course", courseId],
    queryFn: async () => {
      const res = await http.get<CourseWorkspace>(`/lms/courses/${courseId}/`);
      return res.data;
    },
    enabled: !!courseId,
  });
}

export function useCourseMaterials(courseId: number) {
  return useQuery({
    queryKey: ["lms", "materials", courseId],
    queryFn: async () => {
      const res = await http.get<CourseMaterial[]>(`/lms/courses/${courseId}/materials/`);
      return res.data;
    },
    enabled: !!courseId,
  });
}

export function useCourseAnnouncements(courseId: number) {
  return useQuery({
    queryKey: ["lms", "announcements", courseId],
    queryFn: async () => {
      const res = await http.get<CourseAnnouncement[]>(`/lms/courses/${courseId}/announcements/`);
      return res.data;
    },
    enabled: !!courseId,
  });
}

export function useCourseAssignments(courseId: number) {
  return useQuery({
    queryKey: ["lms", "assignments", courseId],
    queryFn: async () => {
      const res = await http.get<Assignment[]>(`/lms/courses/${courseId}/assignments/`);
      return res.data;
    },
    enabled: !!courseId,
  });
}

export function useAssignmentSubmissions(assignmentId: number) {
  return useQuery({
    queryKey: ["lms", "submissions", assignmentId],
    queryFn: async () => {
      const res = await http.get<StudentSubmission[]>(`/lms/assignments/${assignmentId}/submissions/`);
      return res.data;
    },
    enabled: !!assignmentId,
  });
}

export function useSubmitAssignment(assignmentId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { submission_type: string; submission_content: string }) => {
      const res = await http.post<StudentSubmission>(`/lms/assignments/${assignmentId}/submissions/`, payload);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lms", "submissions", assignmentId] });
    },
  });
}

export function useGradeSubmission(submissionId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { points: number; feedback?: string }) => {
      const res = await http.post<Grade>(`/lms/submissions/${submissionId}/grade/`, payload);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lms", "submissions"] });
    },
  });
}

export function useReleaseGrades(assignmentId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const res = await http.post<{ released_count: number }>(`/lms/assignments/${assignmentId}/release-grades/`);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lms", "submissions", assignmentId] });
      queryClient.invalidateQueries({ queryKey: ["lms", "assignments"] });
    },
  });
}
