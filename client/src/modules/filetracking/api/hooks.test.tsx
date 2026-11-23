import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import {
  useArchivedFiles,
  useAuditLogs,
  useCreateFile,
  useFileDetail,
  useFileHistory,
  useForwardFile,
  useInboxFiles,
  useOutboxFiles,
} from "./hooks";

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("filetracking hooks", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("useInboxFiles queries the inbox endpoint", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: [{ id: 1, file_number: "FTS-001" }] });
    const { result } = renderHook(() => useInboxFiles(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(http.get).toHaveBeenCalledWith("/api/v1/filetracking/files/inbox/");
    expect(result.current.data).toHaveLength(1);
  });

  it("useOutboxFiles queries the outbox endpoint", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: [{ id: 2, file_number: "FTS-002" }] });
    const { result } = renderHook(() => useOutboxFiles(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(http.get).toHaveBeenCalledWith("/api/v1/filetracking/files/outbox/");
  });

  it("useArchivedFiles queries the archive endpoint", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: [] });
    const { result } = renderHook(() => useArchivedFiles(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(http.get).toHaveBeenCalledWith("/api/v1/filetracking/files/archived/");
  });

  it("useFileDetail fetches single file detail", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: { id: 10, file_number: "FTS-010" } });
    const { result } = renderHook(() => useFileDetail(10), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(http.get).toHaveBeenCalledWith("/api/v1/filetracking/files/10/");
  });

  it("useFileHistory fetches movement history", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: [] });
    const { result } = renderHook(() => useFileHistory(10), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(http.get).toHaveBeenCalledWith("/api/v1/filetracking/files/10/history/");
  });

  it("useCreateFile posts creation payload", async () => {
    vi.spyOn(http, "post").mockResolvedValue({ data: { id: 20, file_number: "FTS-020" } });
    const { result } = renderHook(() => useCreateFile(), { wrapper });
    result.current.mutate({
      subject: "Test Subject",
      initial_comment: "Test Comment",
      is_draft: false,
      recipient_user_id: 3,
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(http.post).toHaveBeenCalledWith("/api/v1/filetracking/files/", {
      subject: "Test Subject",
      initial_comment: "Test Comment",
      is_draft: false,
      recipient_user_id: 3,
    });
  });

  it("useForwardFile posts forward payload", async () => {
    vi.spyOn(http, "post").mockResolvedValue({ data: { id: 30, action: "FORWARD" } });
    const { result } = renderHook(() => useForwardFile(), { wrapper });
    result.current.mutate({
      fileId: 20,
      recipientUserId: 4,
      recipientDesignation: "Dean",
      comment: "Forwarding for review",
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(http.post).toHaveBeenCalledWith("/api/v1/filetracking/files/20/forward/", {
      recipient_user_id: 4,
      recipient_designation: "Dean",
      comment: "Forwarding for review",
    });
  });

  it("useAuditLogs queries audit trail endpoint", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: [] });
    const { result } = renderHook(() => useAuditLogs(5), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(http.get).toHaveBeenCalledWith("/api/v1/filetracking/governance/audit/?file_id=5");
  });
});
