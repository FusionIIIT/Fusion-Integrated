import { MantineProvider } from "@mantine/core";
import { Notifications, notifications } from "@mantine/notifications";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { vi } from "vitest";
import type { HRRequest } from "../api/types";

const boundary = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn() }));
const access = vi.hoisted(() => ({ permissions: [] as string[] }));
export { boundary, access };
vi.mock("../../../lib/http", async (original) => ({
  ...await original<typeof import("../../../lib/http")>(), http: boundary,
}));
vi.mock("../../../auth/AuthProvider", () => ({
  useAuth: () => ({ can: (permission: string) => access.permissions.includes(permission) }),
}));

export function show(ui: React.ReactElement) {
  const query = new QueryClient({ defaultOptions: {
    queries: { retry: false, gcTime: 0 }, mutations: { retry: false },
  } });
  return { query, ...render(<QueryClientProvider client={query}>
    <MantineProvider><Notifications /><>{ui}</></MantineProvider>
  </QueryClientProvider>) };
}

export function resetBoundary() {
  access.permissions = [];
  notifications.clean();
  boundary.get.mockReset().mockResolvedValue({ data: { results: [] } });
  boundary.post.mockReset().mockResolvedValue({ data: {} });
  boundary.patch.mockReset().mockResolvedValue({ data: {} });
}

export const unavailable = { response: { status: 503,
  data: { error: { message: "Synthetic service unavailable. Retry shortly." } } } };
export const record = { id: 1, user_id: 10, department: "CSE", designation_snapshot: "Professor",
  revision: 1, retirement_status: "", appointment_details: {}, service_history: [],
  leave_balances: { Casual: "4.5" } };
export const claim: HRRequest = { id: 42, user_id: 10, family: "ltc", subtype: "advance", state: "approved",
  payload: { prescribed_form_reference: "official-ltc-form" },
  claim_summary: { purpose: "", amount: null, prescribed_form_reference: "official-ltc-form",
    hr_verified: true, financial_verified: false, payment_status: null, status_history: [] },
  appraisal_summary: null, route_step: 0, route_total_steps: 0,
  submitted_at: "2026-11-21T10:00:00Z", created_at: "2026-11-21T10:00:00Z", updated_at: "2026-11-21T10:00:00Z" };
