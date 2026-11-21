import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { PatentApplication } from "../api/types";
import MyApplicationsPage from "./MyApplicationsPage";

const hooks = vi.hoisted(() => ({
  usePmsApplication: vi.fn(),
  usePmsApplications: vi.fn(),
}));
const auth = vi.hoisted(() => ({ can: vi.fn() }));

vi.mock("../api/hooks", () => hooks);
vi.mock("../../../auth/AuthProvider", () => ({ useAuth: () => auth }));

const application: PatentApplication = {
  id: 41,
  application_no: "PMS-2026-00041",
  title: "Thermal storage controller",
  abstract: "A thermal storage controller.",
  detailed_description: "A complete description of the thermal storage controller.",
  claims: "A controller comprising a thermal sensor.",
  domain: "Energy Systems",
  status: "submitted",
  applicant_user_id: 1001,
  assigned_director_user_id: null,
  assigned_attorney_user_id: null,
  director_assigned_at: null,
  review_deadline: null,
  revision_deadline: null,
  jurisdiction: "IN",
  is_international: false,
  international_justification: "",
  external_filing_id: "",
  external_filing_date: null,
  filing_confirmation: "",
  format_validated: false,
  grant_date: null,
  patent_number: "",
  is_withdrawn: false,
  withdrawal_reason: "",
  withdrawal_date: null,
  created_at: "2026-11-01T00:00:00Z",
  updated_at: "2026-11-01T00:00:00Z",
  coinventors: [],
  documents: [],
  budget: null,
  director_reviews: [],
  attorney_assignments: [],
  office_actions: [],
  maintenance_records: [],
};

function renderPage() {
  return render(
    <MantineProvider>
      <MemoryRouter>
        <MyApplicationsPage />
      </MemoryRouter>
    </MantineProvider>,
  );
}

describe("MyApplicationsPage", () => {
  beforeEach(() => {
    auth.can.mockReturnValue(false);
    hooks.usePmsApplications.mockReturnValue({
      data: [application], isPending: false, error: null,
    });
    hooks.usePmsApplication.mockImplementation((id?: number) => ({
      data: id === application.id ? application : undefined,
      isPending: false,
      error: null,
    }));
  });

  it("shows its loading state", () => {
    hooks.usePmsApplications.mockReturnValue({ data: undefined, isPending: true, error: null });

    renderPage();

    expect(screen.getByRole("heading", { name: "My Applications" })).toBeInTheDocument();
    expect(screen.queryByText("No applications yet")).not.toBeInTheDocument();
  });

  it("shows its empty state", () => {
    hooks.usePmsApplications.mockReturnValue({ data: [], isPending: false, error: null });

    renderPage();

    expect(screen.getByText("No applications yet")).toBeInTheDocument();
  });

  it("shows an API error instead of the list", () => {
    hooks.usePmsApplications.mockReturnValue({
      data: undefined,
      isPending: false,
      error: { response: { data: { error: { message: "Application service unavailable" } } } },
    });

    renderPage();

    expect(screen.getByText("Application service unavailable")).toBeInTheDocument();
    expect(screen.queryByText(application.application_no)).not.toBeInTheDocument();
  });

  it("opens a selected application and hides document controls without permission", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole("button", { name: "Track" }));

    expect(await screen.findByRole("heading", { name: application.application_no })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Record document version" })).not.toBeInTheDocument();
  });
});
