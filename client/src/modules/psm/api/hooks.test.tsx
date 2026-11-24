// HTTP-boundary tests for PSM hooks including CSV export and blob error decoding.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as download from "../../../lib/download";
import { errorMessage, http } from "../../../lib/http";
import { useExportReportCsv } from "./hooks";

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("useExportReportCsv", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(download, "saveBlob").mockImplementation(() => undefined);
  });

  it("downloads the CSV file with the server filename", async () => {
    const blob = new Blob(["indent_number\nIND-1\n"], { type: "text/csv" });
    vi.spyOn(http, "post").mockResolvedValue({
      data: blob,
      headers: { "content-disposition": 'attachment; filename="psm-operational-report.csv"' },
    });
    const { result } = renderHook(() => useExportReportCsv(), { wrapper });
    result.current.mutate({ report_type: "operational" });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(download.saveBlob).toHaveBeenCalledWith(blob, "psm-operational-report.csv");
  });

  it("surfaces error messages encoded in blob error responses", async () => {
    const env = { error: { code: "permission_denied", message: "Report denied.", details: [] } };
    vi.spyOn(http, "post").mockRejectedValue({
      response: { status: 403, data: new Blob([JSON.stringify(env)]) },
    });
    const { result } = renderHook(() => useExportReportCsv(), { wrapper });
    result.current.mutate({ report_type: "financial" });
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(errorMessage(result.current.error)).toBe("Report denied.");
  });
});
