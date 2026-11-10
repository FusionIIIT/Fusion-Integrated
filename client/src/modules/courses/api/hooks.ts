import { useCallback, useEffect, useState } from "react";

import { api } from "../../../lib/api";
import type {
  AnnouncementsResponse,
  AssignmentsResponse,
  CourseAnnouncement,
  CourseAssignment,
  CourseMaterial,
  CourseMaterialSection,
  CourseWorkspaceDetail,
  CreateAnnouncementPayload,
  CreateAssignmentPayload,
  CreateMaterialPayload,
  CreateSectionPayload,
  MaterialsResponse,
  UpdateAnnouncementPayload,
  UpdateAssignmentPayload,
  UpdateMaterialPayload,
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

// ---------------------------------------------------------------------------
// Announcements hooks
// ---------------------------------------------------------------------------

export function useCourseAnnouncements(workspaceId: number | null) {
  const [data, setData] = useState<AnnouncementsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(async () => {
    if (!workspaceId) {
      setData(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await api.get<AnnouncementsResponse>(
        `${BASE}/workspaces/${workspaceId}/announcements`,
      );
      setData(res.data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load announcements");
    } finally {
      setLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return { data, loading, error, refetch };
}

export async function createAnnouncement(
  workspaceId: number,
  payload: CreateAnnouncementPayload,
): Promise<CourseAnnouncement> {
  const { data } = await api.post<CourseAnnouncement>(
    `${BASE}/workspaces/${workspaceId}/announcements`,
    payload,
  );
  return data;
}

export async function updateAnnouncement(
  workspaceId: number,
  announcementId: number,
  payload: UpdateAnnouncementPayload,
): Promise<CourseAnnouncement> {
  const { data } = await api.patch<CourseAnnouncement>(
    `${BASE}/workspaces/${workspaceId}/announcements/${announcementId}`,
    payload,
  );
  return data;
}

export async function deleteAnnouncement(
  workspaceId: number,
  announcementId: number,
): Promise<void> {
  await api.delete(
    `${BASE}/workspaces/${workspaceId}/announcements/${announcementId}`,
  );
}

// ---------------------------------------------------------------------------
// Materials & Sections hooks
// ---------------------------------------------------------------------------

export function useCourseSections(workspaceId: number | null) {
  const [data, setData] = useState<CourseMaterialSection[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(async () => {
    if (!workspaceId) {
      setData([]);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await api.get<CourseMaterialSection[]>(
        `${BASE}/workspaces/${workspaceId}/sections`,
      );
      setData(res.data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load course sections");
    } finally {
      setLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return { data, loading, error, refetch };
}

export function useCourseMaterials(
  workspaceId: number | null,
  sectionId?: number | null,
) {
  const [data, setData] = useState<MaterialsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(async () => {
    if (!workspaceId) {
      setData(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const url =
        sectionId !== undefined && sectionId !== null
          ? `${BASE}/workspaces/${workspaceId}/materials?section_id=${sectionId}`
          : `${BASE}/workspaces/${workspaceId}/materials`;
      const res = await api.get<MaterialsResponse>(url);
      setData(res.data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load course materials");
    } finally {
      setLoading(false);
    }
  }, [workspaceId, sectionId]);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return { data, loading, error, refetch };
}

export async function createSection(
  workspaceId: number,
  payload: CreateSectionPayload,
): Promise<CourseMaterialSection> {
  const { data } = await api.post<CourseMaterialSection>(
    `${BASE}/workspaces/${workspaceId}/sections`,
    payload,
  );
  return data;
}

export async function updateSection(
  workspaceId: number,
  sectionId: number,
  payload: Partial<CreateSectionPayload>,
): Promise<CourseMaterialSection> {
  const { data } = await api.patch<CourseMaterialSection>(
    `${BASE}/workspaces/${workspaceId}/sections/${sectionId}`,
    payload,
  );
  return data;
}

export async function deleteSection(
  workspaceId: number,
  sectionId: number,
): Promise<void> {
  await api.delete(`${BASE}/workspaces/${workspaceId}/sections/${sectionId}`);
}

export async function createMaterial(
  workspaceId: number,
  payload: CreateMaterialPayload,
): Promise<CourseMaterial> {
  const { data } = await api.post<CourseMaterial>(
    `${BASE}/workspaces/${workspaceId}/materials`,
    payload,
  );
  return data;
}

export async function updateMaterial(
  workspaceId: number,
  materialId: number,
  payload: UpdateMaterialPayload,
): Promise<CourseMaterial> {
  const { data } = await api.patch<CourseMaterial>(
    `${BASE}/workspaces/${workspaceId}/materials/${materialId}`,
    payload,
  );
  return data;
}

export async function deleteMaterial(
  workspaceId: number,
  materialId: number,
): Promise<void> {
  await api.delete(`${BASE}/workspaces/${workspaceId}/materials/${materialId}`);
}

// ---------------------------------------------------------------------------
// Assignments hooks
// ---------------------------------------------------------------------------

export function useCourseAssignments(workspaceId: number | null) {
  const [data, setData] = useState<AssignmentsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(async () => {
    if (!workspaceId) {
      setData(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await api.get<AssignmentsResponse>(
        `${BASE}/workspaces/${workspaceId}/assignments`,
      );
      setData(res.data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load assignments");
    } finally {
      setLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return { data, loading, error, refetch };
}

export async function createAssignment(
  workspaceId: number,
  payload: CreateAssignmentPayload,
): Promise<CourseAssignment> {
  const { data } = await api.post<CourseAssignment>(
    `${BASE}/workspaces/${workspaceId}/assignments`,
    payload,
  );
  return data;
}

export async function updateAssignment(
  workspaceId: number,
  assignmentId: number,
  payload: UpdateAssignmentPayload,
): Promise<CourseAssignment> {
  const { data } = await api.patch<CourseAssignment>(
    `${BASE}/workspaces/${workspaceId}/assignments/${assignmentId}`,
    payload,
  );
  return data;
}

export async function deleteAssignment(
  workspaceId: number,
  assignmentId: number,
): Promise<void> {
  await api.delete(
    `${BASE}/workspaces/${workspaceId}/assignments/${assignmentId}`,
  );
}

