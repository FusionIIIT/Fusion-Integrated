// A request needs a published policy, a financial year covering today and a departmental
// allocation. The System Admin puts them in place through the API; each step tolerates what a
// previous run left behind.
import { expect, request } from "@playwright/test";

import { stateFile } from "../support/session";
import { BASE_URL, DEPARTMENT } from "./actors";

const POLICY = {
  approval_timeout_hours: 48,
  ta_high_value_threshold: "25000",
  budget_check_required: true,
  request_types: ["voucher", "reimbursement"],
  required_documents: { expense: 1, ta: 1 },
  routes: [
    { kind: "expense", min_amount: "0", max_amount: "50000", levels: ["iaa_hod"],
      escalation_designation: "iaa_dean" },
    { kind: "expense", min_amount: "50000", levels: ["iaa_hod", "iaa_dean"],
      escalation_designation: "iaa_director" },
    { kind: "ta", min_amount: "0", levels: ["iaa_hod"], escalation_designation: "iaa_dean" },
  ],
  anomaly_resolvers: {
    budget: ["iaa_finance_staff", "iaa_dean"],
    policy: ["iaa_finance_staff", "iaa_director"],
    financial: ["iaa_auditor", "iaa_director"],
  },
};

interface Year { id: number; starts_on: string; ends_on: string }

export async function configureIaa(): Promise<void> {
  const api = await request.newContext({ baseURL: BASE_URL, storageState: stateFile("iaaAdmin") });
  try {
    const me = await api.get("/api/v1/me");
    expect(me.ok(), "the IAA System Admin is signed in").toBe(true);
    const headers = { "X-CSRF-Token": ((await me.json()) as { csrf_token: string }).csrf_token };
    const acting = await api.patch("/api/v1/me", { headers, data: { active_role: "iaa_system_admin" } });
    expect(acting.ok(), "the admin may act as iaa_system_admin").toBe(true);

    const today = new Date().toISOString().slice(0, 10);
    const list = async (): Promise<Year[]> =>
      (await (await api.get("/api/v1/iaa/config/financial-years")).json()) as Year[];
    let year = (await list()).find((y) => y.starts_on <= today && today <= y.ends_on);
    if (!year) {
      const now = new Date().getFullYear();
      const made = await api.post("/api/v1/iaa/config/financial-years", {
        headers, data: { code: `E2E-${now}`, starts_on: `${now}-01-01`, ends_on: `${now}-12-31` },
      });
      expect(made.status(), "a financial year covering today can be added").toBe(201);
      year = (await list()).find((y) => y.starts_on <= today && today <= y.ends_on);
    }
    expect(year, "a financial year covers today").toBeDefined();

    const budget = await api.post("/api/v1/iaa/config/budget-entries", {
      headers, data: { financial_year_id: year?.id, department: DEPARTMENT,
                       kind: "allocation", amount: "100000000" },
    });
    expect(budget.status()).toBe(201);
    const policy = await api.post("/api/v1/iaa/config/policies", { headers, data: POLICY });
    expect(policy.status()).toBe(201);
  } finally {
    await api.dispose();
  }
}
