/** HR-EIS deep-link permissions are enforced before restricted pages mount. */
import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { routes } from "../routes";

const auth = vi.hoisted(() => ({ useAuth: vi.fn() }));
vi.mock("../../../auth/AuthProvider", () => auth);

describe("HR-EIS restricted deep links", () => {
  it("blocks an employee from the approval queue despite request-view permission", () => {
    auth.useAuth.mockReturnValue({
      can: (permission: string) => permission === "hreis.request.view",
    });
    const approvals = routes.find((route) => route.path === "approvals");
    expect(approvals?.element).toBeDefined();
    render(<MantineProvider>{approvals?.element}</MantineProvider>);
    expect(screen.getByText("Not available to your role")).toBeInTheDocument();
    expect(screen.queryByText("Assigned approval queue")).toBeNull();
  });
});
