/** Companies is an office page: registering, approving and inviting all need
 *  company.manage, so a role without it gets the page's refusal and no controls. */
import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Company } from "../api/types";
import CompaniesPage from "./CompaniesPage";

const useAuth = vi.hoisted(() => vi.fn());
vi.mock("../../../auth/AuthProvider", () => ({ useAuth }));

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

function renderAs(permissions: string[]) {
  useAuth.mockReturnValue({ can: (p: string) => permissions.includes(p) });
  return render(<MantineProvider><CompaniesPage /></MantineProvider>);
}

describe("CompaniesPage", () => {
  beforeEach(() => {
    const idle = { mutate: vi.fn(), isPending: false };
    hooks.useCompanies.mockReturnValue(
      { data: { results: [approved, pending] }, isPending: false, error: null });
    hooks.useCompanyDecision.mockReturnValue(idle);
    hooks.useInviteRecruiter.mockReturnValue(idle);
    hooks.useRegisterCompany.mockReturnValue(idle);
  });

  it("tells a role without company.manage the page is not for it, with nothing to press", () => {
    renderAs(["placement_cell.job_posting.view"]);

    expect(screen.getByText("Not available to your role")).toBeInTheDocument();
    expect(screen.queryByRole("button")).toBeNull();
    expect(screen.queryByText("Acme Corp")).toBeNull();
    expect(hooks.useCompanies).toHaveBeenCalledWith({ enabled: false });
  });

  it("gives an officer every control", () => {
    renderAs(["placement_cell.company.manage"]);

    expect(screen.getByRole("button", { name: /register company/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /invite recruiter/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Approve" })).toBeInTheDocument();
    expect(screen.queryByText("Not available to your role")).toBeNull();
    expect(hooks.useCompanies).toHaveBeenCalledWith({ enabled: true });
  });
});
