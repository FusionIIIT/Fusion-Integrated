/** The CSV export path: fetched, not navigated to.
 *
 *  A plain link left the SPA, so a refusal replaced the app with the server's
 *  own error page. These pin the two halves of the fix — the download, and the
 *  error being readable at all.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as download from "../../../lib/download";
import { http } from "../../../lib/http";
import { errorMessage } from "../../../lib/http";
import { useCsvExport } from "./hooks";

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("useCsvExport", () => {
  beforeEach(() => {
    vi.spyOn(download, "saveBlob").mockImplementation(() => undefined);
  });

  it("saves the file under the name the server chose", async () => {
    const blob = new Blob(["Roll no,Name\n21BEC004,ABHAY\n"], { type: "text/csv" });
    vi.spyOn(http, "get").mockResolvedValue({
      data: blob,
      headers: {
        "content-disposition": 'attachment; filename="applications-20260803-1015.csv"',
      },
    });

    const { result } = renderHook(() => useCsvExport(), { wrapper });
    result.current.mutate("applications");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(http.get).toHaveBeenCalledWith(
      "/placement/exports/applications.csv", { responseType: "blob" });
    expect(download.saveBlob).toHaveBeenCalledWith(
      blob, "applications-20260803-1015.csv");
  });

  it("falls back to the export's own name when the header carries none", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: new Blob([]), headers: {} });

    const { result } = renderHook(() => useCsvExport(), { wrapper });
    result.current.mutate("placements");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(download.saveBlob).toHaveBeenCalledWith(expect.any(Blob), "placements.csv");
  });

  it("reads the error envelope back out of the blob body", async () => {
    // responseType "blob" delivers the *error* body as a Blob too, which hides
    // the envelope. Without readBlobError the toast says nothing useful.
    const envelope = {
      error: { code: "permission_denied", message: "Not available.", details: [] },
    };
    vi.spyOn(http, "get").mockRejectedValue({
      response: { status: 403, data: new Blob([JSON.stringify(envelope)]) },
    });

    const { result } = renderHook(() => useCsvExport(), { wrapper });
    result.current.mutate("applications");

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(errorMessage(result.current.error)).toBe("Not available.");
    expect(download.saveBlob).not.toHaveBeenCalled();
  });

  it("survives an error body that is not our envelope", async () => {
    // A raw Django 404 page, for instance: generic beats a crash in the toast.
    vi.spyOn(http, "get").mockRejectedValue({
      response: { status: 404, data: new Blob(["<html>Page not found</html>"]) },
    });

    const { result } = renderHook(() => useCsvExport(), { wrapper });
    result.current.mutate("applications");

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(errorMessage(result.current.error)).toMatch(/something went wrong/i);
  });
});
