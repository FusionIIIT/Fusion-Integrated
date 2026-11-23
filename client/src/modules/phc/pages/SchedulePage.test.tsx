import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import SchedulePage from "./SchedulePage";
import { listStateTests, refusal, renderPage, state } from "./testing";

const http = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), put: vi.fn() }));
vi.mock("../../../lib/http", async (orig) => ({
  ...(await orig<typeof import("../../../lib/http")>()), http,
}));
vi.mock("../../../auth/AuthProvider", () => ({
  useAuth: () => ({ can: (p: string) => state.permissions.has(p) }),
}));

const schedule = { id: 3, doctor_name: "Dr. Iyer", specialization: "General",
  is_published: false, published_at: null, today_status: "available",
  slots: [{ day_of_week: 0, day_label: "Monday", start_time: "10:00:00", end_time: "13:00:00" }] };

describe("SchedulePage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    state.permissions = new Set(["phc.schedule.view"]);
  });

  listStateTests({ get: http.get, page: () => <SchedulePage />, empty: [],
    emptyText: /no doctor schedule/i });

  it("shows a patient the live status and no staff controls", async () => {
    http.get.mockResolvedValue({ data: [schedule] });
    renderPage(<SchedulePage />);
    expect(await screen.findByText("Available")).toBeInTheDocument();
    for (const name of [/new schedule/i, /^edit$/i, /^publish$/i, /mark available/i]) {
      expect(screen.queryByRole("button", { name })).not.toBeInTheDocument();
    }
  });

  it("lets PHC staff publish and mark attendance, showing a refusal", async () => {
    state.permissions = new Set(["phc.schedule.view", "phc.schedule.publish",
      "phc.attendance.update"]);
    http.get.mockResolvedValue({ data: [schedule] });
    http.post.mockRejectedValueOnce(refusal("This schedule is already published.", 409));
    renderPage(<SchedulePage />);
    fireEvent.click(await screen.findByRole("button", { name: /^publish$/i }));
    expect(await screen.findByText("This schedule is already published.")).toBeInTheDocument();
    http.post.mockResolvedValueOnce({ data: {} });
    fireEvent.click(screen.getByRole("button", { name: /mark departed/i }));
    await waitFor(() => expect(http.post).toHaveBeenLastCalledWith(
      "/phc/schedules/3/attendance", { status: "departed" }));
  });

  it("creates a schedule from the form", async () => {
    state.permissions = new Set(["phc.schedule.view", "phc.schedule.create"]);
    http.get.mockResolvedValue({ data: [] });
    http.post.mockResolvedValue({ data: schedule });
    renderPage(<SchedulePage />);
    fireEvent.click(await screen.findByRole("button", { name: /new schedule/i }));
    fireEvent.change(await screen.findByLabelText(/doctor name/i),
      { target: { value: "Dr. Rao" } });
    fireEvent.change(screen.getByLabelText(/^from/i), { target: { value: "09:00" } });
    fireEvent.change(screen.getByLabelText(/^to/i), { target: { value: "11:00" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(http.post).toHaveBeenCalledWith("/phc/schedules", {
      doctor_name: "Dr. Rao", specialization: "",
      slots: [{ day_of_week: 0, start_time: "09:00", end_time: "11:00" }] }));
  });
});
