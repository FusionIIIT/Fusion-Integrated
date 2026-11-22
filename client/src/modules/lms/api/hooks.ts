import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../../lib/http";

const KEY = "lms";

export interface CourseSummary {
  code: string;
  title: string;
  description: string;
  schedule: string;
  status: "draft" | "published";
  role: "faculty" | "student" | "ta" | "observer";
}

export interface CourseStaff {
  user_id: number;
  display_name: string;
  email: string;
  department: string;
}

export interface CourseWorkspaceDetail {
  code: string;
  title: string;
  description: string;
  syllabus: string;
  schedule: string;
  status: "draft" | "published";
  role: "faculty" | "student" | "ta" | "observer";
  can_edit: boolean;
  instructors: CourseStaff[];
  teaching_assistants: CourseStaff[];
}

export interface UpdateCourseWorkspacePayload {
  title?: string;
  description?: string;
  syllabus?: string;
  schedule?: string;
  status?: "draft" | "published";
}

export interface CourseMaterialItem {
  id: number;
  title: string;
  description: string;
  material_type: "file" | "link" | "note";
  section_type: "module" | "week";
  section_title: string;
  file_name: string;
  file_size: number | null;
  has_file: boolean;
  link_url: string;
  content: string;
  status: "draft" | "published" | "scheduled";
  release_at: string | null;
  order: number;
  created_by_user_id: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface CourseMaterialSection {
  section_title: string;
  section_type: "module" | "week";
  materials: CourseMaterialItem[];
}

export interface CourseMaterialsResponse {
  course_code: string;
  course_title: string;
  role: "faculty" | "student" | "ta" | "observer";
  can_manage: boolean;
  sections: CourseMaterialSection[];
  total_count: number;
}

export interface CreateMaterialPayload {
  title: string;
  section_title: string;
  material_type: "file" | "link" | "note";
  section_type: "module" | "week";
  status: "draft" | "published" | "scheduled";
  description?: string;
  link_url?: string;
  content?: string;
  file?: File | null;
  release_at?: string | null;
  order?: number;
}

export interface UpdateMaterialPayload {
  title?: string;
  section_title?: string;
  material_type?: "file" | "link" | "note";
  section_type?: "module" | "week";
  status?: "draft" | "published" | "scheduled";
  description?: string;
  link_url?: string;
  content?: string;
  file?: File | null;
  release_at?: string | null;
  order?: number;
}

export function useCourses() {
  return useQuery({
    queryKey: [KEY, "courses"],
    queryFn: async () => (await http.get<{ results: CourseSummary[] }>("/lms/courses")).data,
  });
}

export function useCourseWorkspace(code: string | null) {
  return useQuery({
    queryKey: [KEY, "workspace", code],
    queryFn: async () => {
      if (!code) return null;
      return (await http.get<CourseWorkspaceDetail>(`/lms/courses/${code}`)).data;
    },
    enabled: Boolean(code),
  });
}

export function useUpdateCourseWorkspace() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ code, body }: { code: string; body: UpdateCourseWorkspacePayload }) =>
      (await http.patch<CourseWorkspaceDetail>(`/lms/courses/${code}`, body)).data,
    onSuccess: (updated) => {
      qc.invalidateQueries({ queryKey: [KEY, "workspace", updated.code] });
      qc.invalidateQueries({ queryKey: [KEY, "courses"] });
    },
  });
}

function toPayloadData(body: Record<string, unknown>): FormData | Record<string, unknown> {
  if (body.file instanceof File) {
    const fd = new FormData();
    for (const [k, v] of Object.entries(body)) {
      if (v !== undefined && v !== null) {
        if (v instanceof File) {
          fd.append(k, v);
        } else {
          fd.append(k, String(v));
        }
      }
    }
    return fd;
  }
  return body;
}

export function useCourseMaterials(code: string | null) {
  return useQuery({
    queryKey: [KEY, "materials", code],
    queryFn: async () => {
      if (!code) return null;
      return (await http.get<CourseMaterialsResponse>(`/lms/courses/${code}/materials`)).data;
    },
    enabled: Boolean(code),
  });
}

export function useCreateMaterial() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ code, body }: { code: string; body: CreateMaterialPayload }) => {
      const payload = toPayloadData(body as unknown as Record<string, unknown>);
      return (await http.post<CourseMaterialItem>(`/lms/courses/${code}/materials`, payload)).data;
    },
    onSuccess: (_, { code }) => {
      qc.invalidateQueries({ queryKey: [KEY, "materials", code] });
    },
  });
}

export function useUpdateMaterial() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      code,
      materialId,
      body,
    }: {
      code: string;
      materialId: number;
      body: UpdateMaterialPayload;
    }) => {
      const payload = toPayloadData(body as unknown as Record<string, unknown>);
      return (
        await http.patch<CourseMaterialItem>(
          `/lms/courses/${code}/materials/${materialId}`,
          payload,
        )
      ).data;
    },
    onSuccess: (_, { code }) => {
      qc.invalidateQueries({ queryKey: [KEY, "materials", code] });
    },
  });
}

export function useDeleteMaterial() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ code, materialId }: { code: string; materialId: number }) => {
      await http.delete(`/lms/courses/${code}/materials/${materialId}`);
      return { code, materialId };
    },
    onSuccess: (_, { code }) => {
      qc.invalidateQueries({ queryKey: [KEY, "materials", code] });
    },
  });
}

export interface CourseAnnouncementItem {
  id: number;
  course_code: string;
  title: string;
  content: string;
  created_by_user_id: number;
  author_name: string;
  author_role: "faculty" | "student" | "ta" | "observer";
  created_at: string | null;
  updated_at: string | null;
}

export interface CourseAnnouncementsResponse {
  course_code: string;
  course_title: string;
  role: "faculty" | "student" | "ta" | "observer";
  can_post: boolean;
  announcements: CourseAnnouncementItem[];
  total_count: number;
}

export interface PostAnnouncementPayload {
  title: string;
  content: string;
}

export function useCourseAnnouncements(code: string | null) {
  return useQuery({
    queryKey: [KEY, "announcements", code],
    queryFn: async () => {
      if (!code) return null;
      return (
        await http.get<CourseAnnouncementsResponse>(`/lms/courses/${code}/announcements`)
      ).data;
    },
    enabled: Boolean(code),
  });
}

export function usePostCourseAnnouncement() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ code, body }: { code: string; body: PostAnnouncementPayload }) => {
      return (
        await http.post<CourseAnnouncementItem>(`/lms/courses/${code}/announcements`, body)
      ).data;
    },
    onSuccess: (_, { code }) => {
      qc.invalidateQueries({ queryKey: [KEY, "announcements", code] });
    },
  });
}

export interface CourseAssignmentItem {
  id: number;
  course_code: string;
  title: string;
  instructions: string;
  submission_type: "file" | "text" | "link";
  points_possible: number;
  status: "draft" | "published" | "scheduled";
  due_at: string | null;
  release_at: string | null;
  closes_at: string | null;
  allow_late: boolean;
  file_name: string;
  file_size: number | null;
  has_file: boolean;
  created_by_user_id: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface CourseAssignmentsResponse {
  course_code: string;
  course_title: string;
  role: "faculty" | "student" | "ta" | "observer";
  can_manage: boolean;
  assignments: CourseAssignmentItem[];
  total_count: number;
}

export interface CreateAssignmentPayload {
  title: string;
  instructions?: string;
  submission_type: "file" | "text" | "link";
  points_possible?: number;
  status: "draft" | "published" | "scheduled";
  due_at?: string | null;
  release_at?: string | null;
  closes_at?: string | null;
  allow_late?: boolean;
  file?: File | null;
}

export interface UpdateAssignmentPayload {
  title?: string;
  instructions?: string;
  submission_type?: "file" | "text" | "link";
  points_possible?: number;
  status?: "draft" | "published" | "scheduled";
  due_at?: string | null;
  release_at?: string | null;
  closes_at?: string | null;
  allow_late?: boolean;
  file?: File | null;
}

export function useCourseAssignments(code: string | null) {
  return useQuery({
    queryKey: [KEY, "assignments", code],
    queryFn: async () => {
      if (!code) return null;
      return (
        await http.get<CourseAssignmentsResponse>(`/lms/courses/${code}/assignments`)
      ).data;
    },
    enabled: Boolean(code),
  });
}

export function useCreateAssignment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ code, body }: { code: string; body: CreateAssignmentPayload }) => {
      const payload = toPayloadData(body as unknown as Record<string, unknown>);
      return (
        await http.post<CourseAssignmentItem>(`/lms/courses/${code}/assignments`, payload)
      ).data;
    },
    onSuccess: (_, { code }) => {
      qc.invalidateQueries({ queryKey: [KEY, "assignments", code] });
    },
  });
}

export function useUpdateAssignment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      code,
      assignmentId,
      body,
    }: {
      code: string;
      assignmentId: number;
      body: UpdateAssignmentPayload;
    }) => {
      const payload = toPayloadData(body as unknown as Record<string, unknown>);
      return (
        await http.patch<CourseAssignmentItem>(
          `/lms/courses/${code}/assignments/${assignmentId}`,
          payload,
        )
      ).data;
    },
    onSuccess: (_, { code }) => {
      qc.invalidateQueries({ queryKey: [KEY, "assignments", code] });
    },
  });
}

export function useDeleteAssignment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ code, assignmentId }: { code: string; assignmentId: number }) => {
      await http.delete(`/lms/courses/${code}/assignments/${assignmentId}`);
      return { code, assignmentId };
    },
    onSuccess: (_, { code }) => {
      qc.invalidateQueries({ queryKey: [KEY, "assignments", code] });
    },
  });
}

export interface AssignmentDeadlineInfo {
  assignment_id: number;
  course_code: string;
  title: string;
  original_due_at: string | null;
  closes_at: string | null;
  allow_late: boolean;
  effective_due_at: string | null;
  is_extended: boolean;
  extension_id: number | null;
  extended_due_at: string | null;
  extension_reason: string;
  window_status: "not_open" | "open" | "late_allowed" | "closed";
  is_submission_allowed: boolean;
  role: "faculty" | "student" | "ta" | "observer";
  can_manage_deadlines: boolean;
  total_extensions: number;
}

export interface AssignmentExtensionItem {
  id: number;
  assignment_id: number;
  user_id: number;
  student_name: string;
  student_email: string;
  extended_due_at: string;
  reason: string;
  granted_by_user_id: number;
  granted_by_name: string;
  created_at: string;
  updated_at: string;
}

export interface GrantExtensionPayload {
  student_user_id: number;
  extended_due_at: string;
  reason?: string;
}

export interface UpdateDeadlineWindowPayload {
  due_at?: string | null;
  closes_at?: string | null;
  allow_late?: boolean;
}

export function useAssignmentDeadline(code: string | null, assignmentId: number | null) {
  return useQuery({
    queryKey: [KEY, "assignments", code, assignmentId, "deadline"],
    queryFn: async () => {
      if (!code || !assignmentId) return null;
      return (
        await http.get<AssignmentDeadlineInfo>(
          `/lms/courses/${code}/assignments/${assignmentId}/deadline`,
        )
      ).data;
    },
    enabled: Boolean(code && assignmentId),
  });
}

export function useAssignmentExtensions(
  code: string | null,
  assignmentId: number | null,
  enabled: boolean = true,
) {
  return useQuery({
    queryKey: [KEY, "assignments", code, assignmentId, "extensions"],
    queryFn: async () => {
      if (!code || !assignmentId) return [];
      return (
        await http.get<AssignmentExtensionItem[]>(
          `/lms/courses/${code}/assignments/${assignmentId}/extensions`,
        )
      ).data;
    },
    enabled: Boolean(code && assignmentId && enabled),
  });
}

export function useUpdateDeadlineWindow() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      code,
      assignmentId,
      body,
    }: {
      code: string;
      assignmentId: number;
      body: UpdateDeadlineWindowPayload;
    }) => {
      return (
        await http.patch<AssignmentDeadlineInfo>(
          `/lms/courses/${code}/assignments/${assignmentId}/window`,
          body,
        )
      ).data;
    },
    onSuccess: (_, { code, assignmentId }) => {
      qc.invalidateQueries({ queryKey: [KEY, "assignments", code] });
      qc.invalidateQueries({
        queryKey: [KEY, "assignments", code, assignmentId, "deadline"],
      });
    },
  });
}

export function useGrantExtension() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      code,
      assignmentId,
      body,
    }: {
      code: string;
      assignmentId: number;
      body: GrantExtensionPayload;
    }) => {
      return (
        await http.post<AssignmentExtensionItem>(
          `/lms/courses/${code}/assignments/${assignmentId}/extensions`,
          body,
        )
      ).data;
    },
    onSuccess: (_, { code, assignmentId }) => {
      qc.invalidateQueries({ queryKey: [KEY, "assignments", code] });
      qc.invalidateQueries({
        queryKey: [KEY, "assignments", code, assignmentId, "deadline"],
      });
      qc.invalidateQueries({
        queryKey: [KEY, "assignments", code, assignmentId, "extensions"],
      });
    },
  });
}

export function useRevokeExtension() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      code,
      assignmentId,
      extensionId,
    }: {
      code: string;
      assignmentId: number;
      extensionId: number;
    }) => {
      await http.delete(
        `/lms/courses/${code}/assignments/${assignmentId}/extensions/${extensionId}`,
      );
      return { code, assignmentId, extensionId };
    },
    onSuccess: (_, { code, assignmentId }) => {
      qc.invalidateQueries({ queryKey: [KEY, "assignments", code] });
      qc.invalidateQueries({
        queryKey: [KEY, "assignments", code, assignmentId, "deadline"],
      });
      qc.invalidateQueries({
        queryKey: [KEY, "assignments", code, assignmentId, "extensions"],
      });
    },
  });
}

export interface CourseSubmissionItem {
  id: number;
  assignment_id: number;
  student_user_id: number;
  submission_type: "file" | "text" | "link";
  status: "submitted" | "late" | "missing";
  submitted_at: string;
  file_name?: string;
  file_size?: number | null;
  has_file: boolean;
  content_text?: string;
  link_url?: string;
  attempt_number: number;
  is_latest: boolean;
  student_name?: string;
  student_email?: string;
}

export interface CourseSubmissionHistory {
  assignment_id: number;
  course_code: string;
  student_user_id: number;
  status: "submitted" | "late" | "missing" | "not_submitted";
  has_submitted: boolean;
  latest_submission: CourseSubmissionItem | null;
  history: CourseSubmissionItem[];
  total_attempts: number;
  deadline_info: AssignmentDeadlineInfo;
}

export interface CourseSubmissionGradeItem {
  id: number;
  submission_id: number;
  assignment_id: number;
  student_user_id: number;
  score: string;
  points_possible: string;
  status: "draft" | "released";
  graded_by_user_id: number;
  graded_by_name: string;
  graded_by_email: string;
  graded_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface RecordGradePayload {
  score: number | string;
}

export interface CourseSubmissionsListEntry {
  student_user_id: number;
  student_name: string;
  student_email: string;
  submission: CourseSubmissionItem | null;
  status: "submitted" | "late" | "missing" | "not_submitted";
  submitted_at: string | null;
  attempt_count: number;
  grade: CourseSubmissionGradeItem | null;
}

export interface CourseSubmissionsListResponse {
  assignment_id: number;
  assignment_title: string;
  course_code: string;
  total_enrolled_students: number;
  total_submissions: number;
  submissions: CourseSubmissionsListEntry[];
}

export interface SubmitAssignmentPayload {
  submission_type: "file" | "text" | "link";
  file?: File | null;
  content_text?: string;
  link_url?: string;
}

export function useStudentSubmission(code: string, assignmentId: number, enabled = true) {
  return useQuery({
    queryKey: [KEY, "assignments", code, assignmentId, "submission", "mine"],
    queryFn: async () => {
      return (
        await http.get<CourseSubmissionHistory>(
          `/lms/courses/${code}/assignments/${assignmentId}/submissions/mine`,
        )
      ).data;
    },
    enabled: Boolean(code) && Boolean(assignmentId) && enabled,
  });
}

export function useAssignmentSubmissions(code: string, assignmentId: number, enabled = true) {
  return useQuery({
    queryKey: [KEY, "assignments", code, assignmentId, "submissions"],
    queryFn: async () => {
      return (
        await http.get<CourseSubmissionsListResponse>(
          `/lms/courses/${code}/assignments/${assignmentId}/submissions`,
        )
      ).data;
    },
    enabled: Boolean(code) && Boolean(assignmentId) && enabled,
  });
}

export function useSubmitAssignment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      code,
      assignmentId,
      body,
    }: {
      code: string;
      assignmentId: number;
      body: SubmitAssignmentPayload;
    }) => {
      let data: FormData | SubmitAssignmentPayload;
      let headers = {};

      if (body.submission_type === "file" && body.file) {
        const formData = new FormData();
        formData.append("submission_type", "file");
        formData.append("file", body.file);
        data = formData;
        headers = { "Content-Type": "multipart/form-data" };
      } else {
        data = body;
      }

      return (
        await http.post<CourseSubmissionItem>(
          `/lms/courses/${code}/assignments/${assignmentId}/submissions/mine`,
          data,
          { headers },
        )
      ).data;
    },
    onSuccess: (_, { code, assignmentId }) => {
      qc.invalidateQueries({ queryKey: [KEY, "assignments", code] });
      qc.invalidateQueries({
        queryKey: [KEY, "assignments", code, assignmentId, "submission", "mine"],
      });
      qc.invalidateQueries({
        queryKey: [KEY, "assignments", code, assignmentId, "submissions"],
      });
    },
  });
}

export function useSubmissionGrade(
  code: string | null,
  assignmentId: number | null,
  submissionId: number | null,
  enabled: boolean = true,
) {
  return useQuery({
    queryKey: [KEY, "assignments", code, assignmentId, "submissions", submissionId, "grade"],
    queryFn: async () => {
      if (!code || !assignmentId || !submissionId) return null;
      return (
        await http.get<CourseSubmissionGradeItem>(
          `/lms/courses/${code}/assignments/${assignmentId}/submissions/${submissionId}/grade`,
        )
      ).data;
    },
    enabled: Boolean(code && assignmentId && submissionId && enabled),
  });
}

export function useRecordSubmissionGrade() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      code,
      assignmentId,
      submissionId,
      body,
    }: {
      code: string;
      assignmentId: number;
      submissionId: number;
      body: RecordGradePayload;
    }) => {
      return (
        await http.post<CourseSubmissionGradeItem>(
          `/lms/courses/${code}/assignments/${assignmentId}/submissions/${submissionId}/grade`,
          body,
        )
      ).data;
    },
    onSuccess: (_, { code, assignmentId, submissionId }) => {
      qc.invalidateQueries({
        queryKey: [KEY, "assignments", code, assignmentId, "submissions"],
      });
      qc.invalidateQueries({
        queryKey: [KEY, "assignments", code, assignmentId, "submissions", submissionId, "grade"],
      });
    },
  });
}
