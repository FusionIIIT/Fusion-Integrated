import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import WorkflowPage from "./WorkflowPage";

const hooks = vi.hoisted(() => ({ useWorkflowOversight: vi.fn() }));
vi.mock("../api/hooks", () => hooks);

describe("WorkflowPage", () => {
  beforeEach(() => {
    hooks.useWorkflowOversight.mockReturnValue({ data: [], isPending: false, error: null });
  });

  it("shows its loading state", () => {
    hooks.useWorkflowOversight.mockReturnValue({ data: undefined, isPending: true, error: null });
    render(<MantineProvider><WorkflowPage /></MantineProvider>);
    expect(screen.getByText("Loading workflow oversight…")).toBeInTheDocument();
  });

  it("shows its empty state", () => {
    render(<MantineProvider><WorkflowPage /></MantineProvider>);
    expect(screen.getByText("No workflow records are available in your authorized scope.")).toBeInTheDocument();
  });

  it("shows its API error state", () => {
    hooks.useWorkflowOversight.mockReturnValue({
      data: undefined,
      isPending: false,
      error: { response: { data: { error: { message: "Workflow service unavailable" } } } },
    });
    render(<MantineProvider><WorkflowPage /></MantineProvider>);
    expect(screen.getByText("Workflow service unavailable")).toBeInTheDocument();
  });

  it("renders workflow records returned by the API", () => {
    hooks.useWorkflowOversight.mockReturnValue({
      data: [{
        application_id: 13,
        application_no: "PMS-2026-00013",
        domain: "Energy Systems",
        status: "under_review",
        assigned_director_user_id: 2001,
        assigned_attorney_user_id: null,
        review_deadline: null,
        revision_deadline: null,
        budget_status: null,
        attorney_assignment_statuses: [],
        office_actions: [],
        maintenance: [],
      }],
      isPending: false,
      error: null,
    });
    render(<MantineProvider><WorkflowPage /></MantineProvider>);
    expect(screen.getByText("PMS-2026-00013 · workflow details")).toBeInTheDocument();
    expect(screen.getByText("under review")).toBeInTheDocument();
  });
});
