import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "../../../auth/AuthProvider";
import { filenameFromDisposition, saveBlob } from "../../../lib/download";
import { http, readBlobError } from "../../../lib/http";
import type { Announcement, Assignment, AssignmentInput, Course, CourseInput, Grade, GradeInput,
  Material, Page, Policy, PolicyInput, ReleaseInput, Section, SectionInput, Submission } from "./types";

function useList<T>(path: string | null) {
  const { session } = useAuth();
  const query = useInfiniteQuery({
    queryKey: ["lms", session?.user.id, session?.active_role, "list", path], enabled: path !== null,
    initialPageParam: path ?? "",
    queryFn: async ({ pageParam }) => (await http.get<Page<T>>(pageParam)).data,
    getNextPageParam: (last) => last.next?.replace(/^.*\/api\/v1/, "") ?? undefined,
  });
  return { ...query, items: query.data?.pages.flatMap((page) => page.results) ?? [] };
}

function useRead<T>(path: string) {
  const { session } = useAuth();
  return useQuery({ queryKey: ["lms", session?.user.id, session?.active_role, "detail", path],
    queryFn: async () => (await http.get<T>(path)).data });
}

function useWrite<T, Input>(path: string, method: "post" | "patch" = "post") {
  const client = useQueryClient();
  return useMutation({ mutationFn: async (data: Input) => (await http[method]<T>(path, data)).data,
    onSuccess: () => client.invalidateQueries({ queryKey: ["lms"] }) });
}

function useDownload(endpoint: (id: number) => string) {
  return useMutation({ mutationFn: async ({ id, fallback }: { id: number; fallback: string }) => {
    try {
      const response = await http.get<Blob>(endpoint(id), { responseType: "blob" });
      saveBlob(response.data, filenameFromDisposition(response.headers["content-disposition"], fallback));
    } catch (error) { throw await readBlobError(error); }
  } });
}

export function useCourses() { return useList<Course>("/lms/courses/"); }
export function useCourse(id: number) { return useRead<Course>(`/lms/courses/${id}/`); }
export function useUpdateCourse(id: number) { return useWrite<Course, CourseInput>(`/lms/courses/${id}/`, "patch"); }
export function useCoursePolicy(id: number) { return useRead<Policy>(`/lms/courses/${id}/policy/`); }
export function useCreatePolicyVersion(id: number) { return useWrite<Policy, PolicyInput>(`/lms/courses/${id}/policy-versions/`); }
export function useCreateSection(id: number) { return useWrite<Section, SectionInput>(`/lms/courses/${id}/sections/`); }
export function useUpdateSection(id: number) { return useWrite<Section, Partial<SectionInput>>(`/lms/sections/${id}/`, "patch"); }
export function useMaterials(id: number) { return useList<Material>(`/lms/courses/${id}/materials/`); }
export function useCreateMaterial(id: number) { return useWrite<Material, FormData>(`/lms/courses/${id}/materials/`); }
export function useMaterial(id: number) { return useRead<Material>(`/lms/materials/${id}/`); }
export function useUpdateMaterial(id: number) { return useWrite<Material, FormData>(`/lms/materials/${id}/`, "patch"); }
export function usePublishMaterial(id: number) { return useWrite<Material, ReleaseInput>(`/lms/materials/${id}/publish/`); }
export function useWithdrawMaterial(id: number) { return useWrite<Material, Record<string, never>>(`/lms/materials/${id}/withdraw/`); }
export function useDownloadMaterial() { return useDownload((id) => `/lms/materials/${id}/download/`); }
export function useAnnouncements(id: number) { return useList<Announcement>(`/lms/courses/${id}/announcements/`); }
export function useCreateAnnouncement(id: number) { return useWrite<Announcement, { content: string }>(`/lms/courses/${id}/announcements/`); }
export function useAssignments(id: number) { return useList<Assignment>(`/lms/courses/${id}/assignments/`); }
export function useCreateAssignment(id: number) { return useWrite<Assignment, AssignmentInput>(`/lms/courses/${id}/assignments/`); }
export function useAssignment(id: number) { return useRead<Assignment>(`/lms/assignments/${id}/`); }
export function useUpdateAssignment(id: number) { return useWrite<Assignment, Partial<AssignmentInput>>(`/lms/assignments/${id}/`, "patch"); }
export function usePublishAssignment(id: number) { return useWrite<Assignment, ReleaseInput>(`/lms/assignments/${id}/publish/`); }
export function useWithdrawAssignment(id: number) { return useWrite<Assignment, Record<string, never>>(`/lms/assignments/${id}/withdraw/`); }
export function useDownloadAssignment() { return useDownload((id) => `/lms/assignments/${id}/download/`); }
export function useSubmissions(id: number | null) { return useList<Submission>(id === null ? null : `/lms/assignments/${id}/submissions/`); }
export function useCreateSubmission(id: number) { return useWrite<Submission, FormData>(`/lms/assignments/${id}/submissions/`); }
export function useSubmission(id: number) { return useRead<Submission>(`/lms/submissions/${id}/`); }
export function useDownloadSubmission() { return useDownload((id) => `/lms/submissions/${id}/download/`); }
export function useSaveGrade(id: number) { return useWrite<Grade, GradeInput>(`/lms/submissions/${id}/grade/`); }
export function useUpdateGrade(id: number) { return useWrite<Grade, GradeInput>(`/lms/submissions/${id}/grade/`, "patch"); }
export function useReleaseGrade(id: number) { return useWrite<Grade, Record<string, never>>(`/lms/submissions/${id}/grade/release/`); }
export function useGrades(id: number) { return useList<Grade>(`/lms/courses/${id}/grades/`); }
