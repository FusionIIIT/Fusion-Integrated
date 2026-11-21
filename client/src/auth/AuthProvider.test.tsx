import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { AuthProvider, useAuth } from "./AuthProvider";

const api = vi.hoisted(() => ({ patch: vi.fn(), get: vi.fn(), post: vi.fn() }));
vi.mock("../lib/http", () => ({
  http: api, errorStatus: vi.fn(), setCsrfToken: vi.fn(), setUnauthorizedHandler: vi.fn(),
}));

function RolePicker() {
  const auth = useAuth();
  return <button onClick={() => auth.switchRole("staff")}>Switch to employee</button>;
}

describe("role switch confidentiality", () => {
  it("removes prior-role cached data before exposing the new session", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const session = { user: { id: 99, kind: "staff" }, active_role: "hradmin",
      roles: ["staff", "hradmin"], permissions: [], modules: ["hreis"], csrf_token: "synthetic" };
    client.setQueryData(["session"], session);
    client.setQueryData(["hreis", "requests", "all"], { results: [{ id: 42, payload: "private" }] });
    api.patch.mockResolvedValue({ data: { ...session, active_role: "staff" } });
    render(<MemoryRouter><QueryClientProvider client={client}>
      <AuthProvider><RolePicker /></AuthProvider>
    </QueryClientProvider></MemoryRouter>);
    fireEvent.click(screen.getByRole("button", { name: "Switch to employee" }));
    await waitFor(() => expect(client.getQueryData(["hreis", "requests", "all"])).toBeUndefined());
    expect(client.getQueryData(["session"])).toMatchObject({ active_role: "staff" });
    client.clear();
  });
});
