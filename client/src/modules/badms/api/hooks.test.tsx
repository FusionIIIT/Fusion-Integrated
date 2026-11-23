import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import {
  useArchivalRequests,
  useAuditLogs,
  useBackups,
  useBackupSchedules,
  useCreateArchivalRequest,
  useCreateRestoration,
  useCreateStorageExtension,
  useDepartmentReport,
  useRestorations,
  useSecurityPolicies,
  useStorageExtensions,
  useTriggerManualBackup,
} from "./hooks";

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("BADMS Hooks", () => {
  it("useBackups fetches backup records", async () => {
    vi.spyOn(http, "get").mockResolvedValue({
      data: {
        results: [
          {
            id: 1,
            backup_type: "manual",
            dataset_name: "fusion_integrated",
            status: "success",
            file_path: "/data/backup.dump",
            file_size_bytes: 1024,
            checksum_sha256: "abc",
            created_at: "2026-11-22T00:00:00Z",
          },
        ],
      },
    });

    const { result } = renderHook(() => useBackups(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.results).toHaveLength(1);
    expect(http.get).toHaveBeenCalledWith("/badms/backups/");
  });

  it("useTriggerManualBackup posts dataset_name", async () => {
    vi.spyOn(http, "post").mockResolvedValue({
      data: { id: 2, status: "pending", dataset_name: "fusion_test" },
    });

    const { result } = renderHook(() => useTriggerManualBackup(), { wrapper });
    result.current.mutate("fusion_test");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(http.post).toHaveBeenCalledWith("/badms/backups/manual/", {
      dataset_name: "fusion_test",
    });
  });

  it("useBackupSchedules fetches schedules", async () => {
    vi.spyOn(http, "get").mockResolvedValue({
      data: {
        results: [
          {
            id: 1,
            name: "Nightly Global",
            cron_expression: "0 2 * * *",
            dataset_name: "fusion_integrated",
            scope_type: "global",
          },
        ],
      },
    });

    const { result } = renderHook(() => useBackupSchedules(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.results[0]?.name).toBe("Nightly Global");
  });

  it("useArchivalRequests and useCreateArchivalRequest operate as expected", async () => {
    vi.spyOn(http, "get").mockResolvedValue({
      data: { results: [{ id: 10, file_name: "archive.zip", status: "submitted" }] },
    });
    vi.spyOn(http, "post").mockResolvedValue({
      data: { id: 11, file_name: "new.zip", status: "submitted" },
    });

    const { result: getResult } = renderHook(() => useArchivalRequests(), { wrapper });
    await waitFor(() => expect(getResult.current.isSuccess).toBe(true));
    expect(getResult.current.data?.results).toHaveLength(1);

    const { result: postResult } = renderHook(() => useCreateArchivalRequest(), { wrapper });
    postResult.current.mutate({
      file_name: "new.zip",
      file_type: "application/zip",
      file_size_bytes: 2048,
      reason: "Course logs",
      file_storage_path: "/data/new.zip",
      initial_classification: "Routine",
    });

    await waitFor(() => expect(postResult.current.isSuccess).toBe(true));
    expect(http.post).toHaveBeenCalledWith("/badms/archival-requests/", expect.objectContaining({
      file_name: "new.zip",
    }));
  });

  it("useStorageExtensions and useCreateStorageExtension operate as expected", async () => {
    vi.spyOn(http, "get").mockResolvedValue({
      data: { results: [{ id: 5, requested_extension_bytes: 5368709120, status: "submitted" }] },
    });
    vi.spyOn(http, "post").mockResolvedValue({
      data: { id: 6, requested_extension_bytes: 10737418240, status: "submitted" },
    });

    const { result: getResult } = renderHook(() => useStorageExtensions(), { wrapper });
    await waitFor(() => expect(getResult.current.isSuccess).toBe(true));
    expect(getResult.current.data?.results).toHaveLength(1);

    const { result: postResult } = renderHook(() => useCreateStorageExtension(), { wrapper });
    postResult.current.mutate({
      requested_extension_bytes: 10737418240,
      justification: "More quota needed",
    });

    await waitFor(() => expect(postResult.current.isSuccess).toBe(true));
    expect(http.post).toHaveBeenCalledWith("/badms/storage-extensions/", expect.objectContaining({
      requested_extension_bytes: 10737418240,
    }));
  });

  it("useRestorations and useCreateRestoration operate as expected", async () => {
    vi.spyOn(http, "get").mockResolvedValue({
      data: { results: [{ id: 8, archival_request_id: 10, status: "submitted" }] },
    });
    vi.spyOn(http, "post").mockResolvedValue({
      data: { id: 9, archival_request_id: 11, status: "submitted" },
    });

    const { result: getResult } = renderHook(() => useRestorations(), { wrapper });
    await waitFor(() => expect(getResult.current.isSuccess).toBe(true));
    expect(getResult.current.data?.results).toHaveLength(1);

    const { result: postResult } = renderHook(() => useCreateRestoration(), { wrapper });
    postResult.current.mutate({
      archival_request_id: 11,
      target_destination: "/restore/path",
    });

    await waitFor(() => expect(postResult.current.isSuccess).toBe(true));
    expect(http.post).toHaveBeenCalledWith("/badms/restorations/", {
      archival_request_id: 11,
      target_destination: "/restore/path",
    });
  });

  it("useAuditLogs fetches audit events", async () => {
    vi.spyOn(http, "get").mockResolvedValue({
      data: { results: [{ id: 1, event_type: "manual_backup_triggered" }] },
    });
    const { result } = renderHook(() => useAuditLogs(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.results[0]?.event_type).toBe("manual_backup_triggered");
  });

  it("useDepartmentReport fetches report when department is non-empty", async () => {
    vi.spyOn(http, "get").mockResolvedValue({
      data: { department: "CSE", total_archival_requests: 5, total_storage_extensions: 2 },
    });
    const { result } = renderHook(() => useDepartmentReport("CSE"), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.department).toBe("CSE");
  });

  it("useSecurityPolicies fetches security policies", async () => {
    vi.spyOn(http, "get").mockResolvedValue({
      data: { results: [{ id: 1, policy_key: "AES_KEY_EXPIRY_DAYS", is_active: true }] },
    });
    const { result } = renderHook(() => useSecurityPolicies(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.results[0]?.policy_key).toBe("AES_KEY_EXPIRY_DAYS");
  });
});
