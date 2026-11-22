import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "../../auth/AuthProvider";
import { http } from "../../lib/http";

interface Page<T> {
  next: string | null;
  results: T[];
}

export function useDepartmentFeed<T>(resource: string, refresh?: number) {
  const { session } = useAuth();
  const query = useInfiniteQuery({
    queryKey: ["department", resource, session?.user.id, session?.active_role],
    initialPageParam: null as string | null,
    queryFn: async ({ pageParam, signal }) => (await http.get<Page<T>>(`/department/${resource}`, {
      params: { cursor: pageParam }, signal,
    })).data,
    getNextPageParam: (page) => page.next
      ? new URL(page.next, window.location.origin).searchParams.get("cursor")
      : null,
    gcTime: 0,
    refetchInterval: refresh,
  });
  return { ...query, rows: query.data?.pages.flatMap((page) => page.results) ?? [] };
}

export function useDepartmentAction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ path, data, method = "post" }: { path: string; data: unknown; method?: "post" | "put" }) =>
      http[method](`/department/${path}`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["department"] }),
  });
}

export function useDepartmentRecord<T>(resource: string, enabled = true) {
  const { session } = useAuth();
  return useQuery({
    queryKey: ["department", resource, session?.user.id, session?.active_role],
    queryFn: async ({ signal }) => (await http.get<T>(`/department/${resource}`, { signal })).data,
    enabled,
    gcTime: 0,
  });
}
