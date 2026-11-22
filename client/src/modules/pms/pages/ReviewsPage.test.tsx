
import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { application } from "./pageTestFixtures";
import ReviewsPage from "./ReviewsPage";

const hooks = vi.hoisted(() => ({
  usePmsApplication: vi.fn(),
  usePmsAppeals: vi.fn(() => ({
    data: [],
    isPending: false,
    error: null,
  })),
  usePmsAction: vi.fn(() => ({
    mutate: vi.fn(),
    isPending: false,
    error: null,
  })),
}));

const auth = vi.hoisted(() => ({ can: vi.fn() }));

vi.mock("../api/hooks", () => hooks);

vi.mock("../../../auth/AuthProvider", () => ({
  useAuth: () => auth,
}));

vi.mock("../components/PmsApplicationSelect", () => ({
  PmsApplicationSelect: ({
    onChange,
  }: {
    onChange: (id: string) => void;
  }) => (
    <button onClick={() => onChange("41")}>
      Select application
    </button>
  ),
}));

describe("ReviewsPage (UC-PMS-007, UC-PMS-008)", () => {
  beforeEach(() => {
    auth.can.mockReturnValue(false);

    hooks.usePmsApplication.mockReturnValue({
      data: { ...application, status: "under_review" },
      isPending: false,
      error: null,
    });

    hooks.usePmsAppeals.mockReturnValue({
      data: [],
      isPending: false,
      error: null,
    });
  });

  it("renders the authorized review action only when the review permission is present", () => {
    const { rerender } = render(
      <MantineProvider>
        <ReviewsPage />
      </MantineProvider>,
    );

    fireEvent.click(
      screen.getByRole("button", { name: "Select application" }),
    );

    expect(
      screen.queryByRole("button", { name: "Record decision" }),
    ).not.toBeInTheDocument();

    auth.can.mockImplementation(
      (permission: string) => permission === "pms.application.review",
    );

    rerender(
      <MantineProvider>
        <ReviewsPage />
      </MantineProvider>,
    );

    expect(
      screen.getByRole("button", { name: "Record decision" }),
    ).toBeInTheDocument();
  });

  it("shows detail loading and API error states", () => {
    hooks.usePmsApplication.mockReturnValue({
      data: undefined,
      isPending: true,
      error: null,
    });

    const { rerender } = render(
      <MantineProvider>
        <ReviewsPage />
      </MantineProvider>,
    );

    fireEvent.click(
      screen.getByRole("button", { name: "Select application" }),
    );

    expect(
      screen.getByText("Loading application…"),
    ).toBeInTheDocument();

    hooks.usePmsApplication.mockReturnValue({
      data: undefined,
      isPending: false,
      error: {
        response: {
          data: {
            error: {
              message: "Review service unavailable",
            },
          },
        },
      },
    });

    rerender(
      <MantineProvider>
        <ReviewsPage />
      </MantineProvider>,
    );

    expect(
      screen.getByText("Review service unavailable"),
    ).toBeInTheDocument();
  });
});
