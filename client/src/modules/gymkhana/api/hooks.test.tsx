import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import { useChangeLeadership, usePeople, useVote } from "./hooks";

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("gymkhana hooks", () => {
  it("does not search the directory for fewer than two characters", () => {
    const get = vi.spyOn(http, "get");
    renderHook(() => usePeople("a", "student"), { wrapper });
    expect(get).not.toHaveBeenCalled();
  });

  it("searches with the kind it was given", async () => {
    const get = vi.spyOn(http, "get").mockResolvedValue({ data: [] });
    const { result } = renderHook(() => usePeople("stu", "faculty"), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(get).toHaveBeenCalledWith("/gymkhana/people", { params: { q: "stu",
      kind: "faculty" } });
  });

  it("puts the id in the path and only the fields in the body", async () => {
    const post = vi.spyOn(http, "post").mockResolvedValue({ data: {} });
    const vote = renderHook(() => useVote(), { wrapper });
    vote.result.current.mutate({ pollId: 4, choice_id: 2 });
    await waitFor(() => expect(post).toHaveBeenCalledWith("/gymkhana/polls/4/votes",
      { choice_id: 2 }));
    const lead = renderHook(() => useChangeLeadership(), { wrapper });
    lead.result.current.mutate({ clubId: 7, coordinator_user_id: 1, co_coordinator_user_id: 2 });
    await waitFor(() => expect(post).toHaveBeenCalledWith("/gymkhana/clubs/7/leadership",
      { coordinator_user_id: 1, co_coordinator_user_id: 2 }));
  });
});
