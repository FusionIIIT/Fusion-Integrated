import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import BookingsPage from "./BookingsPage";
import { http } from "../../lib/http";

const auth = vi.hoisted(() => ({ permissions: [] as string[] }));
vi.mock("../../auth/AuthProvider", () => ({ useAuth: () => ({
  can: (permission: string) => auth.permissions.includes(permission),
  session: { user: { id: 1 }, active_role: "student" },
}) }));
vi.mock("../../lib/http", () => ({ http: { get: vi.fn(), post: vi.fn() }, errorMessage: () => "Request failed" }));
const booking = { id: 1, visitor_name: "Guest", status: "pending", check_in_date: "2026-12-01",
  check_out_date: "2026-12-03", number_of_rooms: 1, cancellation_requested_at: null, bill: null };
function mount() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  render(<QueryClientProvider client={client}><MantineProvider><BookingsPage /></MantineProvider></QueryClientProvider>);
}
beforeEach(() => {
  vi.clearAllMocks(); auth.permissions = [];
  vi.mocked(http.get).mockResolvedValue({ data: { results: [booking], next: null, previous: null } });
  vi.mocked(http.post).mockResolvedValue({ data: {} });
});
describe("hostel bookings", () => {
  it("renders owned bookings without caretaker controls", async () => {
    mount();
    expect(await screen.findByText("#1 · Guest")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Forward" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Request cancellation" })).toBeInTheDocument();
  });
  it("requires explicit confirmation before forwarding", async () => {
    auth.permissions = ["visitor_hostel.booking.manage"];
    mount();
    fireEvent.click(await screen.findByRole("button", { name: "Forward" }));
    expect(http.post).not.toHaveBeenCalled();
    fireEvent.click(await screen.findByRole("button", { name: "Confirm" }));
    await waitFor(() => expect(http.post).toHaveBeenCalledWith(
      "/visitor-hostel/bookings/1/route/", { action: "forward", reason: "" }));
  });
  it("shows server errors without claiming success", async () => {
    vi.mocked(http.get).mockRejectedValue(new Error("Unavailable"));
    mount();
    expect(await screen.findByText("Unable to load bookings")).toBeInTheDocument();
    expect(screen.getByText("Request failed")).toBeInTheDocument();
  });
  it("shows an empty state", async () => {
    vi.mocked(http.get).mockResolvedValue({ data: { results: [], next: null, previous: null } });
    mount();
    expect(await screen.findByText("No bookings to display.")).toBeInTheDocument();
  });
});
