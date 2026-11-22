import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { errorMessage, http } from "../../../lib/http";
import type {
  Announcement,
  Assignment,
  Course,
  CourseMaterial,
  CreateAnnouncementPayload,
  CreateAssignmentPayload,
  CreateMaterialPayload,
  CreateSectionPayload,
  Grade,
  GradeAuditLog,
  GradePayload,
  ModuleSection,
  ScheduledRelease,
  Submission,
  SubmitAssignmentPayload,
  UploadFileResponse,
} from "./types";

export function getFileDownloadUrl(key: string): string {
  return `/api/v1/lms/files/download/?key=${encodeURIComponent(key)}`;
}

export function getApiErrorMessage(err: unknown): string {
  const axiosDetail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
  if (axiosDetail) return axiosDetail;
  return errorMessage(err);
}

export const LMS_KEYS = {
  all: ["lms"] as const,
  courses: () => [...LMS_KEYS.all, "courses"] as const,
  course: (id: number) => [...LMS_KEYS.courses(), id] as const,
  sections: (courseId: number) => [...LMS_KEYS.course(courseId), "sections"] as const,
  materials: (courseId?: number) => [...LMS_KEYS.all, "materials", courseId ?? "all"] as const,
  announcements: (courseId: number) => [...LMS_KEYS.course(courseId), "announcements"] as const,
  assignments: (courseId: number) => [...LMS_KEYS.course(courseId), "assignments"] as const,
  assignment: (id: number) => [...LMS_KEYS.all, "assignments", id] as const,
  submissions: (assignmentId: number) => [...LMS_KEYS.assignment(assignmentId), "submissions"] as const,
  grades: () => [...LMS_KEYS.all, "grades"] as const,
  gradeAuditLogs: (gradeId: number) => [...LMS_KEYS.grades(), gradeId, "audit_logs"] as const,
  scheduledReleases: () => [...LMS_KEYS.all, "scheduled-releases"] as const,
};

export function useCourses() {
  return useQuery({
    queryKey: LMS_KEYS.courses(),
    queryFn: async () => {
      const res = await http.get<Course[]>("/lms/courses/");
      return res.data;
    },
  });
}

export function useCourse(courseId: number) {
  return useQuery({
    queryKey: LMS_KEYS.course(courseId),
    queryFn: async () => {
      const res = await http.get<Course>(`/lms/courses/${courseId}/`);
      return res.data;
    },
    enabled: Number.isFinite(courseId) && courseId > 0,
  });
}

export function useCourseSections(courseId: number) {
  return useQuery({
    queryKey: LMS_KEYS.sections(courseId),
    queryFn: async () => {
      const res = await http.get<ModuleSection[]>(`/lms/courses/${courseId}/sections/`);
      return res.data;
    },
    enabled: Number.isFinite(courseId) && courseId > 0,
  });
}

export function useCourseMaterials(courseId?: number) {
  return useQuery({
    queryKey: LMS_KEYS.materials(courseId),
    queryFn: async () => {
      const url = courseId ? `/lms/materials/?course=${courseId}` : "/lms/materials/";
      const res = await http.get<CourseMaterial[]>(url);
      return res.data;
    },
  });
}

export function useCourseAnnouncements(courseId: number) {
  return useQuery({
    queryKey: LMS_KEYS.announcements(courseId),
    queryFn: async () => {
      const res = await http.get<Announcement[]>(`/lms/courses/${courseId}/announcements/`);
      return res.data;
    },
    enabled: Number.isFinite(courseId) && courseId > 0,
  });
}

export function useCourseAssignments(courseId: number) {
  return useQuery({
    queryKey: LMS_KEYS.assignments(courseId),
    queryFn: async () => {
      const res = await http.get<Assignment[]>(`/lms/courses/${courseId}/assignments/`);
      return res.data;
    },
    enabled: Number.isFinite(courseId) && courseId > 0,
  });
}

export function useAssignment(assignmentId: number) {
  return useQuery({
    queryKey: LMS_KEYS.assignment(assignmentId),
    queryFn: async () => {
      const res = await http.get<Assignment>(`/lms/assignments/${assignmentId}/`);
      return res.data;
    },
    enabled: Number.isFinite(assignmentId) && assignmentId > 0,
  });
}

export function useAssignmentSubmissions(assignmentId: number) {
  return useQuery({
    queryKey: LMS_KEYS.submissions(assignmentId),
    queryFn: async () => {
      const res = await http.get<Submission[]>(`/lms/assignments/${assignmentId}/submissions/`);
      return res.data;
    },
    enabled: Number.isFinite(assignmentId) && assignmentId > 0,
  });
}

export function useGrades() {
  return useQuery({
    queryKey: LMS_KEYS.grades(),
    queryFn: async () => {
      const res = await http.get<Grade[]>("/lms/grades/");
      return res.data;
    },
  });
}

export function useGradeAuditLogs(gradeId: number) {
  return useQuery({
    queryKey: LMS_KEYS.gradeAuditLogs(gradeId),
    queryFn: async () => {
      const res = await http.get<GradeAuditLog[]>(`/lms/grades/${gradeId}/audit_logs/`);
      return res.data;
    },
    enabled: Number.isFinite(gradeId) && gradeId > 0,
  });
}

export function useScheduledReleases() {
  return useQuery({
    queryKey: LMS_KEYS.scheduledReleases(),
    queryFn: async () => {
      const res = await http.get<ScheduledRelease[]>("/lms/scheduled-releases/");
      return res.data;
    },
  });
}

export function useSubmitAssignment(assignmentId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: SubmitAssignmentPayload) => {
      const res = await http.post<Submission>(`/lms/assignments/${assignmentId}/submit/`, payload);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: LMS_KEYS.submissions(assignmentId) });
      qc.invalidateQueries({ queryKey: LMS_KEYS.all });
    },
  });
}

export function useGradeSubmission(submissionId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: GradePayload) => {
      const res = await http.post<Grade>(`/lms/submissions/${submissionId}/grade/`, payload);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: LMS_KEYS.grades() });
      qc.invalidateQueries({ queryKey: LMS_KEYS.all });
    },
  });
}

export function useCreateAnnouncement() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateAnnouncementPayload) => {
      const res = await http.post<Announcement>("/lms/announcements/", payload);
      return res.data;
    },
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: LMS_KEYS.announcements(data.course) });
    },
  });
}

export function useCreateSection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateSectionPayload) => {
      const res = await http.post<ModuleSection>("/lms/sections/", payload);
      return res.data;
    },
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: LMS_KEYS.sections(data.course) });
    },
  });
}

export function useCreateMaterial() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateMaterialPayload) => {
      const res = await http.post<CourseMaterial>("/lms/materials/", payload);
      return res.data;
    },
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: LMS_KEYS.materials(data.course) });
      qc.invalidateQueries({ queryKey: LMS_KEYS.scheduledReleases() });
    },
  });
}

export function useCreateAssignment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateAssignmentPayload) => {
      const res = await http.post<Assignment>("/lms/assignments/", payload);
      return res.data;
    },
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: LMS_KEYS.assignments(data.course) });
      qc.invalidateQueries({ queryKey: LMS_KEYS.scheduledReleases() });
    },
  });
}

export function useUploadFile() {
  return useMutation({
    mutationFn: async (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      const res = await http.post<UploadFileResponse>("/lms/files/upload/", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return res.data;
    },
  });
}
