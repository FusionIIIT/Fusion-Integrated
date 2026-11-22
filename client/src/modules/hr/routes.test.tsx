import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { routes } from "./routes";

const useAuth = vi.hoisted(() => vi.fn());
vi.mock("../../auth/AuthProvider", () => ({ useAuth }));

const guardedRoutes = [
  ["/hr/records", "hr.employee.view_self"],
  ["/hr/employees", "hr.employee.view"],
  ["/hr/claims", "hr.claim.view_self"],
  ["/hr/claims/queue", "hr.claim.view"],
  ["/hr/claims/approvals", "hr.claim.approve"],
  ["/hr/claims/processing", "hr.claim.manage"],
  ["/hr/appraisals", "hr.appraisal.view_self"],
  ["/hr/appraisals/assignment", "hr.appraisal.assign"],
  ["/hr/appraisals/reviews", "hr.appraisal.review"],
  ["/hr/administration", "hr.employee.view"],
  ["/hr/notifications", "hr.notification.view"],
  ["/hr/leaves", "hr.leave.view_self"],
  ["/hr/leaves/queue", "hr.leave.view"],
  ["/hr/leaves/approvals", "hr.leave.approve"],
  ["/hr/leave-balances", "hr.leave_balance.manage"],
] as const;

describe("HR route guards", () => {
  it.each(guardedRoutes)(
    "%s checks its navigation permission and does not mount its page",
    (path, requiredPermission) => {
      const requestedPermissions: string[] = [];
      useAuth.mockReturnValue({
        can: (permission: string) => {
          requestedPermissions.push(permission);
          return false;
        },
      });
      const router = createMemoryRouter(
        [{ path: "/hr", children: routes }],
        { initialEntries: [path] },
      );

      render(
        <MantineProvider>
          <RouterProvider router={router} />
        </MantineProvider>,
      );

      expect(screen.getByText("Not available to your role")).toBeInTheDocument();
      expect(requestedPermissions).toContain(requiredPermission);
      expect(screen.queryByRole("button")).toBeNull();
    },
  );
});
