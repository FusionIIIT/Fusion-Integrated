/** Companies is an office page: who reaches it is the route's guard (routes.tsx);
 *  this pins that an officer who does gets every control. */
import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Company } from "../api/types";
import CompaniesPage from "./CompaniesPage";

const hooks = vi.hoisted(() => ({
  useCompanies: vi.fn(),
  useCompanyDecision: vi.fn(),
  useInviteRecruiter: vi.fn(),
  useRegisterCompany: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

const approved = {
  id: 1, name: "Acme Corp", slug: "acme-corp", sector: "IT", hq_city: "Jabalpur",
  status: "active", approval_status: "approved", approval_note: "",
  approved_at: null, can_operate: true, contacts: [], created_at: "2026-11-01",
} as unknown as Company;
const pending = { ...approved, id: 2, name: "Beta Ltd", approval_status: "pending",
  status: "prospect", can_operate: false } as unknown as Company;

describe("CompaniesPage", () => {
  beforeEach(() => {
    const idle = { mutate: vi.fn(), isPending: false };
    hooks.useCompanies.mockReturnValue(
      { data: { results: [approved, pending] }, isPending: false, error: null });
    hooks.useCompanyDecision.mockReturnValue(idle);
    hooks.useInviteRecruiter.mockReturnValue(idle);
    hooks.useRegisterCompany.mockReturnValue(idle);
  });

  it("gives an officer every control", () => {
    render(<MantineProvider><CompaniesPage /></MantineProvider>);

    expect(screen.getByRole("button", { name: /register company/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /invite recruiter/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Approve" })).toBeInTheDocument();
  });
});
