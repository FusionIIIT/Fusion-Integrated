import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { http } from "../../../lib/http";
import type {
  Assignment,
  AssignmentSubmission,
  Course,
  CourseAnnouncement,
  CourseMaterial,
  CourseMembership,
  GradeChangeAudit,
  SubmissionGrade,
} from "./types";

const KEY = "lms";

export const keys = {
  courses: () => [KEY, "courses"] as const,
  course: (id: number) => [KEY, "course", id] as const,
  roster: (courseId: number) => [KEY, "roster", courseId] as const,
  materials: (courseId: number) => [KEY, "materials", courseId] as const,
  announcements: (courseId?: number) =>
    courseId ? ([KEY, "announcements", courseId] as const) : ([KEY, "announcements"] as const),
  assignments: (courseId?: number) =>
    courseId ? ([KEY, "assignments", courseId] as const) : ([KEY, "assignments"] as const),
  assignment: (id: number) => [KEY, "assignment", id] as const,
  submissions: (assignmentId: number) => [KEY, "submissions", assignmentId] as const,
  myGrades: () => [KEY, "my-grades"] as const,
  gradeAudit: (gradeId: number) => [KEY, "grade-audit", gradeId] as const,
};

function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: [KEY] });
}

// -- Courses -------------------------------------------------------------------
export function useCourses() {
  return useQuery({
    queryKey: keys.courses(),
    queryFn: async () => {
      const { data } = await http.get<Course[]>("/lms/courses/");
      return data;
    },
  });
}

export function useCourse(id: number) {
  return useQuery({
    queryKey: keys.course(id),
    queryFn: async () => {
      const { data } = await http.get<Course>(`/lms/courses/${id}/`);
      return data;
    },
    enabled: !!id,
  });
}

export function useCreateCourse() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<Course>) => {
      const { data } = await http.post<Course>("/lms/courses/", payload);
      return data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useUpdateCourse(courseId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<Course>) => {
      const { data } = await http.patch<Course>(`/lms/courses/${courseId}/`, payload);
      return data;
    },
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Roster --------------------------------------------------------------------
export function useCourseRoster(courseId: number) {
  return useQuery({
    queryKey: keys.roster(courseId),
    queryFn: async () => {
      const { data } = await http.get<CourseMembership[]>(`/lms/courses/${courseId}/roster/`);
      return data;
    },
    enabled: !!courseId,
  });
}

export function useAddCourseMember(courseId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { user_id: number; role: string }) => {
      const { data } = await http.post<CourseMembership>(
        `/lms/courses/${courseId}/roster/`,
        payload,
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.roster(courseId) });
      qc.invalidateQueries({ queryKey: keys.course(courseId) });
    },
  });
}

// -- Materials -----------------------------------------------------------------
export function useCourseMaterials(courseId: number) {
  return useQuery({
    queryKey: keys.materials(courseId),
    queryFn: async () => {
      const { data } = await http.get<CourseMaterial[]>(`/lms/courses/${courseId}/materials/`);
      return data;
    },
    enabled: !!courseId,
  });
}

export function useCreateMaterial(courseId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: FormData | Partial<CourseMaterial>) => {
      const headers = payload instanceof FormData ? { "Content-Type": "multipart/form-data" } : undefined;
      const { data } = await http.post<CourseMaterial>(
        `/lms/courses/${courseId}/materials/`,
        payload,
        { headers },
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.materials(courseId) });
      qc.invalidateQueries({ queryKey: keys.course(courseId) });
    },
  });
}

export function useUpdateMaterial(materialId: number, courseId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<CourseMaterial>) => {
      const { data } = await http.patch<CourseMaterial>(`/lms/materials/${materialId}/`, payload);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.materials(courseId) });
    },
  });
}

export function useDeleteMaterial(materialId: number, courseId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      await http.delete(`/lms/materials/${materialId}/`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.materials(courseId) });
      qc.invalidateQueries({ queryKey: keys.course(courseId) });
    },
  });
}

// -- Announcements -------------------------------------------------------------
export function useCourseAnnouncements(courseId: number) {
  return useQuery({
    queryKey: keys.announcements(courseId),
    queryFn: async () => {
      const { data } = await http.get<CourseAnnouncement[]>(
        `/lms/courses/${courseId}/announcements/`,
      );
      return data;
    },
    enabled: !!courseId,
  });
}

export function useAllAnnouncements() {
  return useQuery({
    queryKey: keys.announcements(),
    queryFn: async () => {
      const { data } = await http.get<CourseAnnouncement[]>("/lms/announcements/");
      return data;
    },
  });
}

export function useCreateAnnouncement(courseId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<CourseAnnouncement>) => {
      const { data } = await http.post<CourseAnnouncement>(
        `/lms/courses/${courseId}/announcements/`,
        payload,
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.announcements(courseId) });
      qc.invalidateQueries({ queryKey: keys.announcements() });
      qc.invalidateQueries({ queryKey: keys.course(courseId) });
    },
  });
}

// -- Assignments ---------------------------------------------------------------
export function useCourseAssignments(courseId: number) {
  return useQuery({
    queryKey: keys.assignments(courseId),
    queryFn: async () => {
      const { data } = await http.get<Assignment[]>(`/lms/courses/${courseId}/assignments/`);
      return data;
    },
    enabled: !!courseId,
  });
}

export function useAllAssignments() {
  return useQuery({
    queryKey: keys.assignments(),
    queryFn: async () => {
      const { data } = await http.get<Assignment[]>("/lms/assignments/");
      return data;
    },
  });
}

export function useAssignment(id: number) {
  return useQuery({
    queryKey: keys.assignment(id),
    queryFn: async () => {
      const { data } = await http.get<Assignment>(`/lms/assignments/${id}/`);
      return data;
    },
    enabled: !!id,
  });
}

export function useCreateAssignment(courseId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<Assignment>) => {
      const { data } = await http.post<Assignment>(
        `/lms/courses/${courseId}/assignments/`,
        payload,
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.assignments(courseId) });
      qc.invalidateQueries({ queryKey: keys.assignments() });
      qc.invalidateQueries({ queryKey: keys.course(courseId) });
    },
  });
}

export function useUpdateAssignment(assignmentId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<Assignment>) => {
      const { data } = await http.patch<Assignment>(`/lms/assignments/${assignmentId}/`, payload);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.assignment(assignmentId) });
      qc.invalidateQueries({ queryKey: keys.assignments() });
    },
  });
}

// -- Submissions ---------------------------------------------------------------
export function useAssignmentSubmissions(assignmentId: number) {
  return useQuery({
    queryKey: keys.submissions(assignmentId),
    queryFn: async () => {
      const { data } = await http.get<AssignmentSubmission[]>(
        `/lms/assignments/${assignmentId}/submissions/`,
      );
      return data;
    },
    enabled: !!assignmentId,
  });
}

export function useSubmitAssignment(assignmentId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: FormData | Partial<AssignmentSubmission>) => {
      const headers = payload instanceof FormData ? { "Content-Type": "multipart/form-data" } : undefined;
      const { data } = await http.post<AssignmentSubmission>(
        `/lms/assignments/${assignmentId}/submissions/`,
        payload,
        { headers },
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.assignment(assignmentId) });
      qc.invalidateQueries({ queryKey: keys.submissions(assignmentId) });
      qc.invalidateQueries({ queryKey: keys.assignments() });
    },
  });
}

// -- Grading & Audit -----------------------------------------------------------
export function useGradeSubmission(submissionId: number, assignmentId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      points_awarded: number;
      feedback?: string;
      change_reason?: string;
    }) => {
      const { data } = await http.post<SubmissionGrade>(
        `/lms/submissions/${submissionId}/grade/`,
        payload,
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.submissions(assignmentId) });
      qc.invalidateQueries({ queryKey: keys.assignment(assignmentId) });
    },
  });
}

export function useReleaseGrades(assignmentId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await http.post<{ released_count: number; message: string }>(
        `/lms/assignments/${assignmentId}/release-grades/`,
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.submissions(assignmentId) });
      qc.invalidateQueries({ queryKey: keys.assignment(assignmentId) });
      qc.invalidateQueries({ queryKey: keys.myGrades() });
    },
  });
}

export function useGradeAuditLogs(gradeId: number) {
  return useQuery({
    queryKey: keys.gradeAudit(gradeId),
    queryFn: async () => {
      const { data } = await http.get<GradeChangeAudit[]>(`/lms/grades/${gradeId}/audit/`);
      return data;
    },
    enabled: !!gradeId,
  });
}

export function useMyGrades() {
  return useQuery({
    queryKey: keys.myGrades(),
    queryFn: async () => {
      const { data } = await http.get<AssignmentSubmission[]>("/lms/grades/my-grades/");
      return data;
    },
  });
}
