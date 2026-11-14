/** An office page reached by a role without its permission says so and never mounts. */
import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { RequirePermission } from "./RequirePermission";

const useAuth = vi.hoisted(() => vi.fn());
vi.mock("./AuthProvider", () => ({ useAuth }));

function renderHolding(permissions: string[]) {
  useAuth.mockReturnValue({ can: (p: string) => permissions.includes(p) });
  const Page = vi.fn(() => <button type="button">Schedule a round</button>);
  render(
    <MantineProvider>
      <RequirePermission permission="placement_cell.interview.schedule"><Page /></RequirePermission>
    </MantineProvider>,
  );
  return Page;
}

describe("RequirePermission", () => {
  it("refuses a role without the permission, and never mounts the page", () => {
    const page = renderHolding(["placement_cell.job_posting.view"]);

    expect(screen.getByText("Not available to your role")).toBeInTheDocument();
    expect(screen.queryByRole("button")).toBeNull();
    expect(page).not.toHaveBeenCalled();
  });

  it("renders the page for a role that holds it", () => {
    renderHolding(["placement_cell.interview.schedule"]);

    expect(screen.getByRole("button", { name: "Schedule a round" })).toBeInTheDocument();
    expect(screen.queryByText("Not available to your role")).toBeNull();
  });
});
