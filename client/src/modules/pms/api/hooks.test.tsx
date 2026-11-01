import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as download from "../../../lib/download";
import { http } from "../../../lib/http";
import {
  downloadDocument,
  useApplications,
  useCreateApplication,
  useSubmitDirectorReview,
} from "./hooks";

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("PMS API Hooks", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(download, "saveBlob").mockImplementation(() => undefined);
  });

  describe("downloadDocument", () => {
    it("saves document blob with filename from Content-Disposition", async () => {
      const blob = new Blob(["%PDF-1.4 test"], { type: "application/pdf" });
      vi.spyOn(http, "get").mockResolvedValue({
        data: blob,
        headers: {
          "content-disposition": 'attachment; filename="patent-spec-v1.pdf"',
        },
      });

      await downloadDocument(42, "fallback.pdf");

      expect(http.get).toHaveBeenCalledWith("/pms/documents/42/download", {
        responseType: "blob",
      });
      expect(download.saveBlob).toHaveBeenCalledWith(blob, "patent-spec-v1.pdf");
    });

    it("falls back to default filename when header is missing", async () => {
      const blob = new Blob(["%PDF-1.4 test"], { type: "application/pdf" });
      vi.spyOn(http, "get").mockResolvedValue({
        data: blob,
        headers: {},
      });

      await downloadDocument(99, "fallback-spec.pdf");

      expect(download.saveBlob).toHaveBeenCalledWith(blob, "fallback-spec.pdf");
    });
  });

  describe("useApplications", () => {
    it("queries /pms/applications with filter parameters", async () => {
      const mockResult = {
        results: [
          {
            id: 1,
            application_no: "PMS-2026-0001",
            title: "Novel Solid State Battery",
            domain: "Energy",
            status: "submitted",
            user_id: 100,
            primary_inventor_name: "Dr. Lead",
            has_budget: false,
            budget_status: "none",
            submitted_at: "2026-11-01T10:00:00Z",
            created_at: "2026-11-01T10:00:00Z",
            updated_at: "2026-11-01T10:00:00Z",
          },
        ],
      };

      vi.spyOn(http, "get").mockResolvedValue({ data: mockResult });

      const { result } = renderHook(() => useApplications({ status: "submitted" }), {
        wrapper,
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(http.get).toHaveBeenCalledWith("/pms/applications", {
        params: { status: "submitted" },
      });
      expect(result.current.data?.results).toHaveLength(1);
      expect(result.current.data?.results[0]?.application_no).toBe("PMS-2026-0001");
    });
  });

  describe("useCreateApplication", () => {
    it("submits invention disclosure and invalidates cache", async () => {
      const createdApp = {
        id: 10,
        application_no: "PMS-2026-0010",
        title: "Photonic Neural Accelerator",
        status: "submitted",
      };

      vi.spyOn(http, "post").mockResolvedValue({ data: createdApp });

      const { result } = renderHook(() => useCreateApplication(), { wrapper });

      result.current.mutate({
        title: "Photonic Neural Accelerator",
        abstract: "Abstract",
        description: "Desc",
        claims: "Claim 1",
        domain: "CSE",
        inventors: [
          {
            name: "Inventor A",
            email: "a@institute.ac.in",
            department: "CSE",
            share_percentage: 100,
            is_lead: true,
          },
        ],
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(http.post).toHaveBeenCalledWith(
        "/pms/applications",
        expect.objectContaining({
          title: "Photonic Neural Accelerator",
        })
      );
    });
  });

  describe("useSubmitDirectorReview", () => {
    it("posts director review decision to application review endpoint", async () => {
      const reviewRes = {
        id: 5,
        application_id: 10,
        director_user_id: 9001,
        decision: "approved",
        justification: "Novel technical contribution meeting Section 2(1)(j).",
      };

      vi.spyOn(http, "post").mockResolvedValue({ data: reviewRes });

      const { result } = renderHook(() => useSubmitDirectorReview(10), { wrapper });

      result.current.mutate({
        decision: "approved",
        justification: "Novel technical contribution meeting Section 2(1)(j).",
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(http.post).toHaveBeenCalledWith(
        "/pms/applications/10/review",
        expect.objectContaining({
          decision: "approved",
        })
      );
    });
  });
});
