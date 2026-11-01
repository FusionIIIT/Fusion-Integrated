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
