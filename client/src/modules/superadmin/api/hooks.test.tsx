import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import {
  useArchivedUsers,
  useAuditLogs,
  useCreatePurgeRequest,
  useDashboard,
  useDecidePurgeRequest,
  useExecutePurge,
  useHistoricalArchives,
  usePolicyParams,
  usePurgeRequests,
  useRestoreUser,
  useSupersedePolicyParam,
} from "./hooks";

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("superadmin api hooks", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe("useDashboard", () => {
    it("fetches dashboard operational metrics", async () => {
      const mockMetrics = {
        archived_users_reversible: 3,
        archived_users_total: 12,
        purge_requests_pending: 2,
        audit_logs_total: 45,
      };
      vi.spyOn(http, "get").mockResolvedValue({ data: mockMetrics });

      const { result } = renderHook(() => useDashboard(), { wrapper });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(http.get).toHaveBeenCalledWith("/api/v1/superadmin/dashboard/");
      expect(result.current.data).toEqual(mockMetrics);
    });
  });

  describe("useArchivedUsers", () => {
    it("fetches archived users with filter params", async () => {
      const mockPage = { count: 1, next: null, previous: null, results: [{ user_id: 1, username: "user01", status: "reversible" }] };
      vi.spyOn(http, "get").mockResolvedValue({ data: mockPage });

      const filters = { status: "reversible", search: "user" };
      const { result } = renderHook(() => useArchivedUsers(filters), { wrapper });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(http.get).toHaveBeenCalledWith("/api/v1/superadmin/archival/users/", { params: filters });
      expect(result.current.data).toEqual(mockPage);
    });
  });

  describe("useHistoricalArchives", () => {
    it("fetches historical datasets", async () => {
      const mockPage = { count: 1, next: null, previous: null, results: [{ id: 1, dataset_category: "placement" }] };
      vi.spyOn(http, "get").mockResolvedValue({ data: mockPage });

      const { result } = renderHook(() => useHistoricalArchives(), { wrapper });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(http.get).toHaveBeenCalledWith("/api/v1/superadmin/archival/datasets/", { params: undefined });
      expect(result.current.data).toEqual(mockPage);
    });
  });

  describe("useRestoreUser", () => {
    it("posts user restoration request", async () => {
      const mockResponse = { user_id: 101, status: "restored" };
      vi.spyOn(http, "post").mockResolvedValue({ data: mockResponse });

      const { result } = renderHook(() => useRestoreUser(), { wrapper });
      result.current.mutate({ user_id: 101, restoration_reason: "Court order" });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(http.post).toHaveBeenCalledWith(
        "/api/v1/superadmin/archival/users/101/restore/",
        { restoration_reason: "Court order" },
      );
      expect(result.current.data).toEqual(mockResponse);
    });
  });

  describe("usePurgeRequests", () => {
    it("fetches purge requests with filters", async () => {
      const mockPage = { count: 1, next: null, previous: null, results: [{ id: 10, status: "pending_it_head" }] };
      vi.spyOn(http, "get").mockResolvedValue({ data: mockPage });

      const filters = { status: "pending_it_head" };
      const { result } = renderHook(() => usePurgeRequests(filters), { wrapper });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(http.get).toHaveBeenCalledWith("/api/v1/superadmin/purge/requests/", { params: filters });
      expect(result.current.data).toEqual(mockPage);
    });
  });

  describe("useCreatePurgeRequest", () => {
    it("creates a dual-auth purge request", async () => {
      const mockResponse = { id: 5, archive: 2, status: "pending_it_head" };
      vi.spyOn(http, "post").mockResolvedValue({ data: mockResponse });

      const { result } = renderHook(() => useCreatePurgeRequest(), { wrapper });
      result.current.mutate({ archive_id: 2, request_reason: "Mandatory purge" });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(http.post).toHaveBeenCalledWith(
        "/api/v1/superadmin/purge/requests/",
        { archive_id: 2, request_reason: "Mandatory purge" },
      );
      expect(result.current.data).toEqual(mockResponse);
    });
  });

  describe("useDecidePurgeRequest", () => {
    it("submits approval decision for purge request", async () => {
      const mockResponse = { id: 5, status: "approved" };
      vi.spyOn(http, "post").mockResolvedValue({ data: mockResponse });

      const { result } = renderHook(() => useDecidePurgeRequest(), { wrapper });
      result.current.mutate({ id: 5, approve: true, comments: "Approved by IT Head" });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(http.post).toHaveBeenCalledWith(
        "/api/v1/superadmin/purge/requests/5/decision/",
        { approve: true, comments: "Approved by IT Head" },
      );
      expect(result.current.data).toEqual(mockResponse);
    });
  });

  describe("useExecutePurge", () => {
    it("executes approved purge request", async () => {
      const mockResponse = { id: 5, status: "purged" };
      vi.spyOn(http, "post").mockResolvedValue({ data: mockResponse });

      const { result } = renderHook(() => useExecutePurge(), { wrapper });
      result.current.mutate(5);

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(http.post).toHaveBeenCalledWith(
        "/api/v1/superadmin/purge/requests/5/execute/",
        {},
      );
      expect(result.current.data).toEqual(mockResponse);
    });
  });

  describe("usePolicyParams", () => {
    it("fetches active policy parameters", async () => {
      const mockPage = { count: 1, next: null, previous: null, results: [{ id: 1, key: "archival.window", value: "30" }] };
      vi.spyOn(http, "get").mockResolvedValue({ data: mockPage });

      const { result } = renderHook(() => usePolicyParams(), { wrapper });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(http.get).toHaveBeenCalledWith("/api/v1/superadmin/policy/parameters/");
      expect(result.current.data).toEqual(mockPage);
    });
  });

  describe("useSupersedePolicyParam", () => {
    it("submits superseded policy parameter", async () => {
      const mockResponse = { id: 1, key: "archival.window", value: "60", version: 2 };
      vi.spyOn(http, "post").mockResolvedValue({ data: mockResponse });

      const { result } = renderHook(() => useSupersedePolicyParam(), { wrapper });
      result.current.mutate({ key: "archival.window", value: "60", description: "Updated window" });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(http.post).toHaveBeenCalledWith(
        "/api/v1/superadmin/policy/parameters/",
        { key: "archival.window", value: "60", description: "Updated window" },
      );
      expect(result.current.data).toEqual(mockResponse);
    });
  });

  describe("useAuditLogs", () => {
    it("fetches audit log entries with filters", async () => {
      const mockPage = { count: 1, next: null, previous: null, results: [{ id: 1, action: "purge.executed" }] };
      vi.spyOn(http, "get").mockResolvedValue({ data: mockPage });

      const filters = { action: "purge.executed" };
      const { result } = renderHook(() => useAuditLogs(filters), { wrapper });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(http.get).toHaveBeenCalledWith("/api/v1/superadmin/audit/logs/", { params: filters });
      expect(result.current.data).toEqual(mockPage);
    });
  });
});
