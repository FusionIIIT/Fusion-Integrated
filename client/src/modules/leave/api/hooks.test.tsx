import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import { parseHolidays } from "../pages/CalendarPage";
import { useRequestAction } from "./hooks";

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("leave hooks", () => {
  it("posts a request action to its own endpoint", async () => {
    vi.spyOn(http, "post").mockResolvedValue({ data: {} });
    const { result } = renderHook(() => useRequestAction(), { wrapper });
    result.current.mutate({ id: 7, action: "review", body: { decision: "approve" } });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(http.post).toHaveBeenCalledWith("/leave/requests/7/review",
      { decision: "approve" });
  });

  it("reads restricted and closed holidays from text lines", () => {
    expect(parseHolidays("2027-01-26, Republic Day, closed\n\n2027-03-22, Holi, restricted"))
      .toEqual([
        { date: "2027-01-26", name: "Republic Day", kind: "closed" },
        { date: "2027-03-22", name: "Holi", kind: "restricted" },
      ]);
  });
});
