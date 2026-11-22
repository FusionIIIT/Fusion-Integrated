import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AdvisoriesPage from "./AdvisoriesPage";
import { listStateTests, refusal, renderPage, state } from "./testing";

const http = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), put: vi.fn() }));
vi.mock("../../../lib/http", async (orig) => ({
  ...(await orig<typeof import("../../../lib/http")>()), http,
}));
vi.mock("../../../auth/AuthProvider", () => ({
  useAuth: () => ({ can: (p: string) => state.permissions.has(p) }),
}));

const page = { results: [{ id: 1, title: "Dengue", body: "Remove water.",
  published_at: "2026-11-23T09:00:00Z" }], next: null, previous: null };

describe("AdvisoriesPage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    state.permissions = new Set(["phc.advisory.view"]);
  });

  listStateTests({ get: http.get, page: () => <AdvisoriesPage />,
    empty: { results: [], next: null, previous: null }, emptyText: /no health advisories/i });

  it("hides publishing from a patient", async () => {
    http.get.mockResolvedValue({ data: page });
    renderPage(<AdvisoriesPage />);
    expect(await screen.findByText("Dengue")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /publish advisory/i })).not.toBeInTheDocument();
  });

  it("lets PHC staff publish, and shows the server's refusal", async () => {
    state.permissions.add("phc.advisory.publish");
    http.get.mockResolvedValue({ data: page });
    http.post.mockRejectedValueOnce(refusal("The advisory text is required.", 400));
    renderPage(<AdvisoriesPage />);
    fireEvent.click(await screen.findByRole("button", { name: /publish advisory/i }));
    fireEvent.change(await screen.findByLabelText(/title/i), { target: { value: "Heat" } });
    fireEvent.change(screen.getByLabelText(/^advisory/i), { target: { value: "Drink water" } });
    fireEvent.click(screen.getByRole("button", { name: "Publish" }));
    expect(await screen.findByText("The advisory text is required.")).toBeInTheDocument();
    http.post.mockResolvedValueOnce({ data: page.results[0] });
    fireEvent.click(screen.getByRole("button", { name: "Publish" }));
    await waitFor(() => expect(http.post).toHaveBeenLastCalledWith("/phc/advisories",
      { title: "Heat", body: "Drink water" }));
  });
});
