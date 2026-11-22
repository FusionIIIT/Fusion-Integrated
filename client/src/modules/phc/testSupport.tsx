import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, type RenderResult } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import type { ComponentType, ReactNode } from "react";
import { expect, it, vi } from "vitest";
import { AuthProvider } from "../../auth/AuthProvider";
import { http } from "../../lib/http";

export const allPermissions = [
  "phc.doctor_schedule.view", "phc.doctor_schedule.create", "phc.doctor_schedule.update",
  "phc.doctor_schedule.publish", "phc.doctor_attendance.update",
  "phc.patient_record.view", "phc.patient_record.create", "phc.record.export",
  "phc.reimbursement.view", "phc.reimbursement.create", "phc.reimbursement.review",
  "phc.reimbursement.manage", "phc.reimbursement.approve", "phc.inventory.view",
  "phc.inventory.create", "phc.inventory.update", "phc.requisition.view",
  "phc.requisition.create", "phc.requisition.approve", "phc.requisition.update",
  "phc.ambulance_usage.view", "phc.ambulance_usage.create", "phc.advisory.view",
  "phc.advisory.publish", "phc.report.view", "phc.notification.view",
];

export const session = {
  user: { id: 1001, username: "test-user", display_name: "Test User",
    kind: "faculty", email: "" },
  active_role: "faculty",
  roles: ["faculty"],
  permissions: allPermissions,
  modules: ["phc"],
  navigation: [],
  csrf_token: "test-csrf",
};

export function pageData(url: string) {
  if (url.endsWith("/me")) return session;
  if (url.endsWith("/doctor-availability")) return [];
  if (url.includes("/directory/patients")) return [];
  if (url.includes("/reports/")) return { report_type: "visits", data: { total: 0 } };
  return { results: [], next: null, previous: null };
}

export function renderPage(Page: ComponentType, permissions = allPermissions,
  resultMode: "default" | "error" | "pending" = "default",
  overrides: Record<string, unknown> = {}): RenderResult {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const pageSession = { ...session, permissions };
  vi.spyOn(http, "get").mockImplementation(async (url) => {
    if (url === "/me") return { data: pageSession } as never;
    if (resultMode === "error") throw new Error("PHC endpoint failed");
    if (resultMode === "pending") return new Promise(() => undefined);
    return { data: overrides[String(url)] ?? pageData(String(url)) } as never;
  });
  const Wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter><AuthProvider>{children}</AuthProvider></MemoryRouter>
    </QueryClientProvider>
  );
  const result = render(<Page />, { wrapper: Wrapper });
  return result;
}

export function testPageStates(Page: ComponentType, emptyText: string) {
  it("shows a loading state", async () => {
    renderPage(Page, allPermissions, "pending");
    expect(await screen.findByRole("status")).toBeInTheDocument();
  });

  it("shows the empty state", async () => {
    renderPage(Page);
    expect(await screen.findByText(emptyText)).toBeInTheDocument();
  });

  it("shows the server error instead of loading forever", async () => {
    renderPage(Page, allPermissions, "error");
    expect(await screen.findByRole("alert")).toBeInTheDocument();
  });
}
