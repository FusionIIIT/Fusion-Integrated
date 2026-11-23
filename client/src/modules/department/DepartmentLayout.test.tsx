import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useRoutes } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";

import { routes } from "./routes";
import { http } from "../../lib/http";
import { DepartmentLayout, RequireDepartmentPermission } from "./DepartmentLayout";

vi.mock("../../auth/AuthProvider", () => ({
  useAuth: () => ({ can: () => true, session: { user: { id: 10 }, active_role: "student" } }),
}));
vi.mock("../../lib/http", async (original) => ({
  ...await original<typeof import("../../lib/http")>(), http: { get: vi.fn() },
}));

function show() {
  render(<MantineProvider><QueryClientProvider client={new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })}><MemoryRouter initialEntries={["/department/details"]}><Routes>
    <Route path="/department" element={<DepartmentLayout />}>
      <Route path="details" element={<RequireDepartmentPermission permission="department.details.view">
        <div>Protected details</div>
      </RequireDepartmentPermission>} />
    </Route>
  </Routes></MemoryRouter></QueryClientProvider></MantineProvider>);
}

beforeEach(() => { vi.mocked(http.get).mockReset(); });

it("shows loading while the acting-role permissions are unknown", () => {
  vi.mocked(http.get).mockImplementation(() => new Promise(() => {}));
  show();
  expect(screen.getByLabelText("Loading Department access")).toBeInTheDocument();
  expect(screen.queryByText("Protected details")).not.toBeInTheDocument();
});

it("refuses a direct route when the current role lacks its permission", async () => {
  vi.mocked(http.get).mockResolvedValue({ data: { permissions: [] } });
  show();
  expect(await screen.findByText("Not available to your role")).toBeInTheDocument();
  expect(screen.queryByText("Protected details")).not.toBeInTheDocument();
});

it("renders a route only after its permission is confirmed", async () => {
  vi.mocked(http.get).mockResolvedValue({ data: { permissions: ["department.details.view"] } });
  show();
  expect(await screen.findByText("Protected details")).toBeInTheDocument();
});

it("shows an actionable error when access lookup fails", async () => {
  vi.mocked(http.get).mockRejectedValue(new Error("Network failure"));
  show();
  expect(await screen.findByText("Could not load this")).toBeInTheDocument();
  expect(screen.queryByText("Protected details")).not.toBeInTheDocument();
});

function ProductionRoutes() {
  return useRoutes([{ path: "/department", children: routes }]);
}

it.each([
  ["details", "department.details.view"], ["announcements", "department.announcement.view"],
  ["inventory", "department.stock.view"], ["stock-requests", "department.stock_request.view"],
  ["feedback", "department.feedback.create"], ["feedback-inbox", "department.feedback.view"],
  ["notices", "department.notice.view"], ["labs", "department.lab.view"],
  ["timetable", "department.timetable.view"],
])("denies the production %s route before mounting the page", async (path, permission) => {
  vi.mocked(http.get).mockResolvedValue({ data: { permissions: [] } });
  const route = routes[0]?.children?.find((entry) => entry.path === path);
  expect(route?.element).toHaveProperty("props.permission", permission);
  render(<MantineProvider><QueryClientProvider client={new QueryClient()}>
    <MemoryRouter initialEntries={[`/department/${path}`]}><ProductionRoutes /></MemoryRouter>
  </QueryClientProvider></MantineProvider>);
  expect(await screen.findByText("Not available to your role")).toBeInTheDocument();
  expect(screen.queryAllByRole("button")).toHaveLength(0);
});
