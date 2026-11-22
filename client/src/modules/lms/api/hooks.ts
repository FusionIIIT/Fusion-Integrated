import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "../../../auth/AuthProvider";

import { filenameFromDisposition, saveBlob } from "../../../lib/download";
import { http, readBlobError } from "../../../lib/http";
import type { Course, Page, Policy } from "./types";

export function useLmsList<T>(path: string | null) {
  const { session } = useAuth();
  const query = useInfiniteQuery({
    queryKey: ["lms", session?.user.id, session?.active_role, "list", path], enabled: path !== null,
    initialPageParam: path ?? "",
    queryFn: async ({ pageParam }) => (await http.get<Page<T>>(pageParam)).data,
    getNextPageParam: (last) => last.next?.replace(/^.*\/api\/v1/, "") ?? undefined,
  });
  return { ...query, items: query.data?.pages.flatMap((page) => page.results) ?? [] };
}

export function useCourses() { return useLmsList<Course>("/lms/courses/"); }

export function useCourse(id: number) {
  const { session } = useAuth();
  return useQuery({ queryKey: ["lms", session?.user.id, session?.active_role, "course", id],
    queryFn: async () => (await http.get<Course>(`/lms/courses/${id}/`)).data });
}

export function useCoursePolicy(id: number) {
  const { session } = useAuth();
  return useQuery({ queryKey: ["lms", session?.user.id, session?.active_role, "policy", id],
    queryFn: async () => (await http.get<Policy>(`/lms/courses/${id}/policy/`)).data });
}

interface Write { path: string; data?: object | FormData; method?: "post" | "patch" }
export function useLmsWrite() {
  const client = useQueryClient();
  return useMutation({ mutationFn: async ({ path, data = {}, method = "post" }: Write) =>
    (await http[method](path, data)).data as unknown,
    onSuccess: () => client.invalidateQueries({ queryKey: ["lms"] }),
  });
}

export function useLmsDownload() {
  return useMutation({ mutationFn: async ({ path, fallback }: { path: string; fallback: string }) => {
    try {
      const response = await http.get<Blob>(path, { responseType: "blob" });
      saveBlob(response.data, filenameFromDisposition(response.headers["content-disposition"], fallback));
    } catch (error) { throw await readBlobError(error); }
  } });
}
