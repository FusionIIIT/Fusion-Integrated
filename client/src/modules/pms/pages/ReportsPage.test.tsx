import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ReportsPage from "./ReportsPage";

const hooks = vi.hoisted(() => ({ usePmsReports: vi.fn() }));
vi.mock("../api/hooks", () => hooks);

describe("ReportsPage", () => {
  beforeEach(() => {
    hooks.usePmsReports.mockReturnValue({
      data: { total_applications: 0, status_distribution: {}, domain_distribution: {} },
      isPending: false,
      error: null,
    });
  });

  it("shows its loading state", () => {
    hooks.usePmsReports.mockReturnValue({ data: undefined, isPending: true, error: null });
    render(<MantineProvider><ReportsPage /></MantineProvider>);
    expect(screen.getByText("Loading report…")).toBeInTheDocument();
  });

  it("shows empty aggregates", () => {
    render(<MantineProvider><ReportsPage /></MantineProvider>);
    expect(screen.getByText("No status data.")).toBeInTheDocument();
    expect(screen.getByText("No domain data.")).toBeInTheDocument();
  });

  it("shows its API error state", () => {
    hooks.usePmsReports.mockReturnValue({
      data: undefined,
      isPending: false,
      error: { response: { data: { error: { message: "Reporting service unavailable" } } } },
    });
    render(<MantineProvider><ReportsPage /></MantineProvider>);
    expect(screen.getByText("Reporting service unavailable")).toBeInTheDocument();
  });

  it("renders aggregate values returned by the API", () => {
    hooks.usePmsReports.mockReturnValue({
      data: {
        total_applications: 3,
        status_distribution: { submitted: 2, under_review: 1 },
        domain_distribution: { "Energy Systems": 3 },
      },
      isPending: false,
      error: null,
    });
    render(<MantineProvider><ReportsPage personal /></MantineProvider>);
    expect(screen.getByRole("heading", { name: "My application report" })).toBeInTheDocument();
    expect(screen.getByText("Visible applications").parentElement).toHaveTextContent("3");
    expect(screen.getByText("Energy Systems")).toBeInTheDocument();
  });
});
