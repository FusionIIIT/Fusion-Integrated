/** The behaviours the screens lean on: a gate refusal is an outcome and not an exception, the
 *  credential kind is chosen by shape, and exports are fetched and saved, not navigated to. */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as download from "../../../lib/download";
import { http } from "../../../lib/http";
import { apiError } from "../test-utils";
import { useCheckOut, useReportExport, useValidate } from "./hooks";

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("useValidate", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("sends a six-digit code as an OTP and anything else as a QR token", async () => {
    const post = vi.spyOn(http, "post").mockResolvedValue({ data: { detail: "Checked in." } });
    const { result } = renderHook(() => useValidate(), { wrapper });

    result.current.mutate({ credential: " 123456 ", gate_id: 4 });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(post).toHaveBeenLastCalledWith("/vms/gate/validate", { otp: "123456", gate_id: 4 });

    result.current.mutate({ credential: "a1b2c3d4e5f6a7b8", gate_id: 4 });
    await waitFor(() => expect(post).toHaveBeenCalledTimes(2));
    expect(post).toHaveBeenLastCalledWith(
      "/vms/gate/validate", { qr_token: "a1b2c3d4e5f6a7b8", gate_id: 4 });
  });

  it("returns a 403 denial as data, with its failures, instead of throwing", async () => {
    vi.spyOn(http, "post").mockRejectedValue(Object.assign(new Error("denied"), {
      response: { status: 403, data: {
        detail: "The pass has expired.", code: "outside_validity", override_eligible: true,
        failures: [{ code: "outside_validity", rule: "VMS-BR-190", message: "The pass has expired." }],
      } },
    }));
    const { result } = renderHook(() => useValidate(), { wrapper });
    result.current.mutate({ credential: "abc", gate_id: 1 });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toMatchObject({
      detail: "The pass has expired.", code: "outside_validity", override_eligible: true });
  });

  it("still throws for anything that is not a gate refusal", async () => {
    vi.spyOn(http, "post").mockRejectedValue(apiError(500, "boom"));
    const { result } = renderHook(() => useValidate(), { wrapper });
    result.current.mutate({ credential: "abc", gate_id: 1 });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("useCheckOut", () => {
  it("trims the credential and sends no gate when none is given", async () => {
    const post = vi.spyOn(http, "post").mockResolvedValue({ data: { detail: "Checked out." } });
    const { result } = renderHook(() => useCheckOut(), { wrapper });
    result.current.mutate({ credential: "  tok  " });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(post).toHaveBeenCalledWith("/vms/visit/check-out", { credential: "tok", gate_id: null });
  });
});

describe("useReportExport", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(download, "saveBlob").mockImplementation(() => undefined);
  });

  it("fetches a PDF as a blob and saves it under the server's filename", async () => {
    const blob = new Blob(["%PDF-1.4"], { type: "application/pdf" });
    const get = vi.spyOn(http, "get").mockResolvedValue({
      data: blob,
      headers: { "content-disposition": 'attachment; filename="vms-daily_summary-2026.pdf"' },
    });
    const { result } = renderHook(() => useReportExport(), { wrapper });
    result.current.mutate({ key: "daily_summary", params: { start: "2026-01-01" }, fmt: "pdf" });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(get).toHaveBeenCalledWith("/vms/reports/daily_summary/export", {
      params: { start: "2026-01-01", fmt: "pdf" }, responseType: "blob" });
    expect(download.saveBlob).toHaveBeenCalledWith(blob, "vms-daily_summary-2026.pdf");
  });

  it("falls back to a name built from the report and format", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: new Blob([]), headers: {} });
    const { result } = renderHook(() => useReportExport(), { wrapper });
    result.current.mutate({ key: "audit_trail", params: {}, fmt: "csv" });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(download.saveBlob).toHaveBeenCalledWith(expect.any(Blob), "audit_trail.csv");
  });

  it("surfaces the server's refusal readably even though the body arrived as a blob", async () => {
    const body = new Blob([JSON.stringify({ error: { message: "Not allowed to export." } })]);
    vi.spyOn(http, "get").mockRejectedValue(
      Object.assign(new Error("403"), { response: { status: 403, data: body } }));
    const { result } = renderHook(() => useReportExport(), { wrapper });
    result.current.mutate({ key: "audit_trail", params: {}, fmt: "pdf" });
    await waitFor(() => expect(result.current.isError).toBe(true));
    const { errorMessage } = await import("../../../lib/http");
    expect(errorMessage(result.current.error)).toBe("Not allowed to export.");
    expect(download.saveBlob).not.toHaveBeenCalled();
  });
});
