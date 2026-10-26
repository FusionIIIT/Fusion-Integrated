/** The application download and the queue's acting-role contract, with the network stubbed. */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as download from "../../../lib/download";
import { errorMessage, http } from "../../../lib/http";
import { useApply, useDecide, useDownloadApplication, useQueue } from "./hooks";

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("useDownloadApplication", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(download, "saveBlob").mockImplementation(() => undefined);
  });

  it("saves the document under the server's filename", async () => {
    const blob = new Blob(["<html></html>"], { type: "text/html" });
    vi.spyOn(http, "get").mockResolvedValue({
      data: blob, headers: { "content-disposition": 'attachment; filename="leave-42.html"' },
    });
    const { result } = renderHook(() => useDownloadApplication(), { wrapper });
    result.current.mutate(42);
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(http.get).toHaveBeenCalledWith("/leave/requests/42/document", { responseType: "blob" });
    expect(download.saveBlob).toHaveBeenCalledWith(blob, "leave-42.html");
  });

  it("surfaces a 404 envelope from inside the blob", async () => {
    const body = new Blob([JSON.stringify({ error: { code: "not_found",
      message: "No such leave request.", details: [], request_id: "r1" } })]);
    vi.spyOn(http, "get").mockRejectedValue({ response: { status: 404, data: body } });
    const { result } = renderHook(() => useDownloadApplication(), { wrapper });
    result.current.mutate(7);
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(errorMessage(result.current.error)).toBe("No such leave request.");
  });
});

describe("leave writes and reads", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("posts an application to the requests collection", async () => {
    vi.spyOn(http, "post").mockResolvedValue({ data: { id: 1, status: "awaiting_unit_head" } });
    const { result } = renderHook(() => useApply(), { wrapper });
    result.current.mutate({ category: "CL", start_date: "2026-03-09", end_date: "2026-03-09",
      purpose: "x" });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(http.post).toHaveBeenCalledWith("/leave/requests", expect.objectContaining({
      category: "CL", start_date: "2026-03-09" }));
  });

  it("decides a task by id with the action and remarks", async () => {
    vi.spyOn(http, "post").mockResolvedValue({ data: { id: 3, status: "rejected" } });
    const { result } = renderHook(() => useDecide(), { wrapper });
    result.current.mutate({ id: 9, action: "reject", remarks: "Exams week" });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(http.post).toHaveBeenCalledWith("/leave/tasks/9/decide",
      { action: "reject", remarks: "Exams week" });
  });

  it("reads the queue without client-side filtering", async () => {
    const rows = [{ id: 1 }, { id: 2 }];
    vi.spyOn(http, "get").mockResolvedValue({ data: rows });
    const { result } = renderHook(() => useQueue(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(rows);
  });
});
