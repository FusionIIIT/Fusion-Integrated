import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import { useSchemes, useSubmitApplication } from "./hooks";

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("SPACS hooks", () => {
  it("fetches active schemes", async () => {
    vi.spyOn(http, "get").mockResolvedValue({
      data: [
        { id: 1, name: "Merit Scheme", scheme_code: "MERIT-1", scheme_type: "scholarship" },
      ],
    });

    const { result } = renderHook(() => useSchemes(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toHaveLength(1);
    expect(http.get).toHaveBeenCalledWith("/api/v1/spacs/schemes");
  });

  it("submits application successfully", async () => {
    vi.spyOn(http, "post").mockResolvedValue({
      data: {
        id: 10,
        application_id: "SPACS-APP-010",
        state: "submitted",
      },
    });

    const { result } = renderHook(() => useSubmitApplication(), { wrapper });
    result.current.mutate({
      scheme_code: "MERIT-1",
      academic_cycle: "2026-27",
      cpi: 8.5,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(http.post).toHaveBeenCalledWith("/api/v1/spacs/applications", {
      scheme_code: "MERIT-1",
      academic_cycle: "2026-27",
      cpi: 8.5,
    });
  });
});
