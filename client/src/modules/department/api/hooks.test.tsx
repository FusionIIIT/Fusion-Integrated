import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import { useAnnouncements, useDepartments, usePublishAnnouncement } from "./hooks";

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("Department API Hooks", () => {
  it("fetches list of departments", async () => {
    vi.spyOn(http, "get").mockResolvedValue({
      data: [{ id: 1, code: "CSE", name: "Computer Science" }],
    });

    const { result } = renderHook(() => useDepartments(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual([
      { id: 1, code: "CSE", name: "Computer Science" },
    ]);
    expect(http.get).toHaveBeenCalledWith("/department/departments/");
  });

  it("fetches announcements filtered by department", async () => {
    vi.spyOn(http, "get").mockResolvedValue({
      data: [{ id: 10, title: "Lab Schedule", body: "Lab details..." }],
    });

    const { result } = renderHook(() => useAnnouncements(1), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual([
      { id: 10, title: "Lab Schedule", body: "Lab details..." },
    ]);
    expect(http.get).toHaveBeenCalledWith("/department/announcements/?department=1");
  });

  it("publishes an announcement via mutation", async () => {
    vi.spyOn(http, "post").mockResolvedValue({
      data: { id: 11, title: "Notice", body: "Content" },
    });

    const { result } = renderHook(() => usePublishAnnouncement(), { wrapper });
    result.current.mutate({
      department: 1,
      title: "Notice",
      body: "Content",
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(http.post).toHaveBeenCalledWith("/department/announcements/", {
      department: 1,
      title: "Notice",
      body: "Content",
    });
  });
});
