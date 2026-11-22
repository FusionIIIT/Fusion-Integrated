import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AmbulancePage from "./AmbulancePage";
import { listStateTests, refusal, renderPage, state } from "./testing";

const http = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), put: vi.fn() }));
vi.mock("../../../lib/http", async (orig) => ({
  ...(await orig<typeof import("../../../lib/http")>()), http,
}));
vi.mock("../../../auth/AuthProvider", () => ({
  useAuth: () => ({ can: (p: string) => state.permissions.has(p) }),
}));

const page = (rows: unknown[]) => ({ results: rows, next: null, previous: null });
const row = { id: 1, used_at: "2026-11-23T08:40:00Z", patient_name: "Hostel resident",
  destination: "District Hospital", created_at: "2026-11-23T09:00:00Z" };

describe("AmbulancePage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    state.permissions = new Set(["phc.ambulance.view"]);
  });

  listStateTests({ get: http.get, page: () => <AmbulancePage />, empty: page([]),
    emptyText: /no ambulance use logged/i });

  it("hides logging without phc.ambulance.create", async () => {
    http.get.mockResolvedValue({ data: page([row]) });
    renderPage(<AmbulancePage />);
    expect(await screen.findByText("District Hospital")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /log ambulance use/i })).not.toBeInTheDocument();
  });

  it("logs a use and shows the server's refusal", async () => {
    state.permissions.add("phc.ambulance.create");
    http.get.mockResolvedValue({ data: page([]) });
    http.post.mockRejectedValueOnce(refusal("The ambulance use cannot be logged in the future.",
      400));
    renderPage(<AmbulancePage />);
    fireEvent.click(await screen.findByRole("button", { name: /log ambulance use/i }));
    fireEvent.change(await screen.findByLabelText(/date and time/i),
      { target: { value: "2026-11-23T08:40" } });
    fireEvent.change(screen.getByLabelText(/patient name/i), { target: { value: "A" } });
    fireEvent.change(screen.getByLabelText(/destination/i), { target: { value: "B" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByText("The ambulance use cannot be logged in the future."))
      .toBeInTheDocument();
    await waitFor(() => expect(http.post).toHaveBeenCalledTimes(1));
  });
});
