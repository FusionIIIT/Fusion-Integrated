import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import * as download from "../../../lib/download";
import { errorMessage, http } from "../../../lib/http";
import { useApplications, useDownloadVersion, useExport, usePeople, useUploadDocument } from "./hooks";

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false },
    mutations: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("pms hooks", () => {
  afterEach(() => vi.restoreAllMocks());

  it("sends list filters as query parameters", async () => {
    const get = vi.spyOn(http, "get").mockResolvedValue({ data: { results: [] } });
    const { result } = renderHook(() => useApplications({ q: "anode" }), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(get).toHaveBeenCalledWith("/pms/applications", { params: { q: "anode" } });
  });

  it("uploads the PDF as multipart form data with its fields", async () => {
    const post = vi.spyOn(http, "post").mockResolvedValue({ data: [] });
    const { result } = renderHook(() => useUploadDocument(), { wrapper });
    const file = new File(["%PDF-1.7"], "spec.pdf", { type: "application/pdf" });
    result.current.mutate({ id: 7, file, kind: "claims", title: "Claims", document_id: null });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const [url, form] = post.mock.calls[0] as [string, FormData];
    expect(url).toBe("/pms/applications/7/documents");
    expect(form.get("file")).toBe(file);
    expect(form.get("kind")).toBe("claims");
    expect(form.has("document_id")).toBe(false);
  });

  it("saves a downloaded version under the server's name", async () => {
    const save = vi.spyOn(download, "saveBlob").mockImplementation(() => undefined);
    const blob = new Blob(["%PDF"]);
    vi.spyOn(http, "get").mockResolvedValue({ data: blob,
      headers: { "content-disposition": 'attachment; filename="claims-v2.pdf"' } });
    const { result } = renderHook(() => useDownloadVersion(), { wrapper });
    result.current.mutate({ id: 3, name: "fallback.pdf" });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(save).toHaveBeenCalledWith(blob, "claims-v2.pdf");
  });

  it("reads the refusal back out of a blob error body", async () => {
    vi.spyOn(download, "saveBlob").mockImplementation(() => undefined);
    const body = new Blob([JSON.stringify({ error: { code: "not_found",
      message: "No such document.", details: [], request_id: "r" } })]);
    vi.spyOn(http, "get").mockRejectedValue({ response: { status: 404, data: body } });
    const { result } = renderHook(() => useExport(), { wrapper });
    result.current.mutate({ path: "audit/export", name: "a.csv" });
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(errorMessage(result.current.error)).toBe("No such document.");
  });

  it("asks for people only after two letters", async () => {
    const get = vi.spyOn(http, "get").mockResolvedValue({ data: { results: [] } });
    const { rerender, result } = renderHook(({ q }) => usePeople(q), { wrapper,
      initialProps: { q: "a" } });
    expect(result.current.fetchStatus).toBe("idle");
    rerender({ q: "as" });
    await waitFor(() => expect(get).toHaveBeenCalledWith("/pms/people",
      { params: { q: "as", kind: undefined } }));
  });
});
