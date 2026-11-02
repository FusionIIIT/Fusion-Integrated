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

