import { useCallback, useEffect, useState } from "react";

import { api } from "../../../lib/api";
import type {
  CourseWorkspaceDetail,
  UpdateWorkspacePayload,
  WorkspacesResponse,
} from "./types";

const BASE = "/api/v1/courses";

export function useWorkspaces() {
  const [data, setData] = useState<WorkspacesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get<WorkspacesResponse>(`${BASE}/workspaces`);
      setData(res.data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load courses");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return { data, loading, error, refetch };
}

export function useWorkspaceDetail(id: number | null) {
  const [data, setData] = useState<CourseWorkspaceDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(async () => {
    if (!id) {
      setData(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await api.get<CourseWorkspaceDetail>(`${BASE}/workspaces/${id}`);
      setData(res.data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load course workspace");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return { data, loading, error, refetch };
}

export async function updateWorkspace(id: number, payload: UpdateWorkspacePayload) {
  const { data } = await api.patch<CourseWorkspaceDetail>(
    `${BASE}/workspaces/${id}`,
    payload,
  );
  return data;
}
