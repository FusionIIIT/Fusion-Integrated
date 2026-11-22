/** Data access hooks for the LMS module. */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  Assignment,
  AssignmentSubmission,
  CourseAnnouncement,
  CourseMaterial,
  CourseWorkspaceDetail,
  CourseWorkspaceSummary,
  GradeChangeAudit,
  SubmissionGrade,
} from "./types";

const KEY = "lms";

export const keys = {
  courses: () => [KEY, "courses"] as const,
  course: (id: number) => [KEY, "course", id] as const,
  materials: (courseId?: number) => [KEY, "materials", courseId] as const,
  announcements: (courseId?: number) => [KEY, "announcements", courseId] as const,
  assignments: (courseId?: number) => [KEY, "assignments", courseId] as const,
  submissions: (assignmentId?: number) => [KEY, "submissions", assignmentId] as const,
  submission: (submissionId?: number) => [KEY, "submission", submissionId] as const,
  grade: (submissionId?: number) => [KEY, "grade", submissionId] as const,
  audits: (submissionId?: number) => [KEY, "audits", submissionId] as const,
};

function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: [KEY] });
}

// ---------------------------------------------------------------------------
// Workspaces
// ---------------------------------------------------------------------------

export function useCourses() {
  return useQuery({
    queryKey: keys.courses(),
    queryFn: async () => {
      const { data } = await http.get<CourseWorkspaceSummary[]>("/lms/courses/");
      return data;
    },
  });
}

export function useCourseDetail(courseId: number | null) {
  return useQuery({
    queryKey: keys.course(courseId ?? 0),
    enabled: !!courseId,
    queryFn: async () => {
      const { data } = await http.get<CourseWorkspaceDetail>(`/lms/courses/${courseId}/`);
      return data;
    },
  });
}

export function useUpdateCourse() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      courseId,
      ...payload
    }: {
      courseId: number;
      syllabus?: string;
      schedule_info?: string;
    }) => {
      const { data } = await http.patch<CourseWorkspaceDetail>(
        `/lms/courses/${courseId}/`,
        payload
      );
      return data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

// ---------------------------------------------------------------------------
// Materials
// ---------------------------------------------------------------------------

export function useMaterials(courseId: number | null) {
  return useQuery({
    queryKey: keys.materials(courseId ?? 0),
    enabled: !!courseId,
    queryFn: async () => {
      const { data } = await http.get<CourseMaterial[]>(`/lms/materials/?course_id=${courseId}`);
      return data;
    },
  });
}

export function useCreateMaterial() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: FormData | Record<string, unknown>) => {
      const isForm = payload instanceof FormData;
      const { data } = await http.post<CourseMaterial>("/lms/materials/", payload, {
        headers: isForm ? { "Content-Type": "multipart/form-data" } : undefined,
      });
      return data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useDeleteMaterial() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (materialId: number) => {
      await http.delete(`/lms/materials/${materialId}/`);
    },
    onSuccess: () => invalidateAll(qc),
  });
}

// ---------------------------------------------------------------------------
// Announcements
// ---------------------------------------------------------------------------

export function useAnnouncements(courseId: number | null) {
  return useQuery({
    queryKey: keys.announcements(courseId ?? 0),
    enabled: !!courseId,
    queryFn: async () => {
      const { data } = await http.get<CourseAnnouncement[]>(
        `/lms/announcements/?course_id=${courseId}`
      );
      return data;
    },
  });
}

export function useCreateAnnouncement() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { course_id: number; title: string; content: string }) => {
      const { data } = await http.post<CourseAnnouncement>("/lms/announcements/", payload);
      return data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useDeleteAnnouncement() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (announcementId: number) => {
      await http.delete(`/lms/announcements/${announcementId}/`);
    },
    onSuccess: () => invalidateAll(qc),
  });
}

// ---------------------------------------------------------------------------
// Assignments
// ---------------------------------------------------------------------------

export function useAssignments(courseId: number | null) {
  return useQuery({
    queryKey: keys.assignments(courseId ?? 0),
    enabled: !!courseId,
    queryFn: async () => {
      const { data } = await http.get<Assignment[]>(`/lms/assignments/?course_id=${courseId}`);
      return data;
    },
  });
}

export function useCreateAssignment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      course_id: number;
      title: string;
      instructions: string;
      points_possible: number | string;
      submission_type: string;
      due_date: string;
      release_date?: string | null;
    }) => {
      const { data } = await http.post<Assignment>("/lms/assignments/", payload);
      return data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function usePublishAssignment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      assignmentId,
      release_date,
    }: {
      assignmentId: number;
      release_date?: string | null;
    }) => {
      const { data } = await http.post<Assignment>(`/lms/assignments/${assignmentId}/publish/`, {
        release_date,
      });
      return data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

// ---------------------------------------------------------------------------
// Submissions & Grading
// ---------------------------------------------------------------------------

export function useSubmissions(assignmentId: number | null) {
  return useQuery({
    queryKey: keys.submissions(assignmentId ?? 0),
    enabled: !!assignmentId,
    queryFn: async () => {
      const { data } = await http.get<AssignmentSubmission[]>(
        `/lms/assignments/${assignmentId}/submissions/`
      );
      return data;
    },
  });
}

export function useSubmitAssignment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      assignmentId,
      payload,
    }: {
      assignmentId: number;
      payload: FormData | Record<string, unknown>;
    }) => {
      const isForm = payload instanceof FormData;
      const { data } = await http.post<AssignmentSubmission>(
        `/lms/assignments/${assignmentId}/submissions/`,
        payload,
        {
          headers: isForm ? { "Content-Type": "multipart/form-data" } : undefined,
        }
      );
      return data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useSubmissionGrade(submissionId: number | null) {
  return useQuery({
    queryKey: keys.grade(submissionId ?? 0),
    enabled: !!submissionId,
    queryFn: async () => {
      const { data } = await http.get<SubmissionGrade>(`/lms/submissions/${submissionId}/grade/`);
      return data;
    },
    retry: false,
  });
}

export function useGradeSubmission() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      submissionId,
      ...payload
    }: {
      submissionId: number;
      points_awarded: number | string;
      feedback_text?: string;
    }) => {
      const { data } = await http.post<SubmissionGrade>(
        `/lms/submissions/${submissionId}/grade/`,
        payload
      );
      return data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useUpdateGrade() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      submissionId,
      ...payload
    }: {
      submissionId: number;
      points_awarded: number | string;
      feedback_text?: string;
      reason?: string;
    }) => {
      const { data } = await http.patch<SubmissionGrade>(
        `/lms/submissions/${submissionId}/grade/`,
        payload
      );
      return data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function usePublishGrades() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      assignmentId,
      submission_ids,
    }: {
      assignmentId: number;
      submission_ids?: number[];
    }) => {
      const { data } = await http.post<{ published_count: number }>(
        `/lms/assignments/${assignmentId}/publish-grades/`,
        { submission_ids }
      );
      return data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useGradeAudits(submissionId: number | null) {
  return useQuery({
    queryKey: keys.audits(submissionId ?? 0),
    enabled: !!submissionId,
    queryFn: async () => {
      const { data } = await http.get<GradeChangeAudit[]>(
        `/lms/submissions/${submissionId}/grade-audit/`
      );
      return data;
    },
  });
}
