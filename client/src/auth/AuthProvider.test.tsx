import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider, useAuth } from "./AuthProvider";
import { http, setUnauthorizedHandler } from "../lib/http";

vi.mock("../lib/http", () => ({
  http: { get: vi.fn(), patch: vi.fn(), post: vi.fn() },
  setCsrfToken: vi.fn(), setUnauthorizedHandler: vi.fn(), errorStatus: () => 500,
}));
const session = { user: { id: 1 }, roles: ["student", "staff"], active_role: "student",
  permissions: [], modules: [], csrf_token: "token" };
function Consumer() {
  const auth = useAuth();
  return <><span>{auth.status}</span><button onClick={() => auth.switchRole("staff")}>Switch role</button></>;
}
function mount() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  qc.setQueryData(["private-bookings"], [{ visitor_name: "Private" }]);
  render(<QueryClientProvider client={qc}><MemoryRouter><AuthProvider><Consumer /></AuthProvider></MemoryRouter></QueryClientProvider>);
  return qc;
}
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(http.get).mockResolvedValue({ data: session });
  vi.mocked(http.patch).mockResolvedValue({ data: { ...session, active_role: "staff" } });
});
describe("session data isolation", () => {
  it("removes previous role data on a successful role switch", async () => {
    const qc = mount();
    await screen.findByText("authenticated");
    fireEvent.click(screen.getByRole("button", { name: "Switch role" }));
    await waitFor(() => expect(qc.getQueryData(["private-bookings"])).toBeUndefined());
    expect(qc.getQueryData(["session"])).toMatchObject({ active_role: "staff" });
  });
  it("removes cached private records when the session expires", async () => {
    const qc = mount();
    await screen.findByText("authenticated");
    const handler = vi.mocked(setUnauthorizedHandler).mock.calls.at(-1)?.[0];
    expect(handler).toBeDefined();
    act(() => handler?.());
    expect(qc.getQueryData(["private-bookings"])).toBeUndefined();
    expect(qc.getQueryData(["session"])).toBeNull();
  });
});
