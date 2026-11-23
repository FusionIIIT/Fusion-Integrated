import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import React from "react";
import { MemoryRouter, Route, Routes, useRoutes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { RequireAuth } from "../../auth/RequireAuth";
import { routes } from "./routes";

const useAuth = vi.hoisted(() => vi.fn());
vi.mock("../../auth/AuthProvider", () => ({ useAuth }));

vi.mock("./pages/MyComplaintsPage", () => ({
  default: () => <div data-testid="page-mine">My Complaints Page</div>,
}));
vi.mock("./pages/ComplaintQueuePage", () => ({
  default: () => <div data-testid="page-queue">Complaint Queue Page</div>,
}));
vi.mock("./pages/SupervisorPage", () => ({
  default: () => <div data-testid="page-supervisor">Supervisor Page</div>,
}));
vi.mock("./pages/AnnouncementsPage", () => ({
  default: () => <div data-testid="page-announcements">Announcements Page</div>,
}));
vi.mock("./pages/ReportsPage", () => ({
  default: () => <div data-testid="page-reports">Reports Page</div>,
}));
vi.mock("./pages/RolesPage", () => ({
  default: () => <div data-testid="page-roles">Roles Page</div>,
}));

function ComplaintsRoutes() {
  const element = useRoutes(routes);
  return <React.Suspense fallback={<div>Loading...</div>}>{element}</React.Suspense>;
}

function renderAt(path: string, permissions: string[] = [], status: "authenticated" | "anonymous" = "authenticated") {
  useAuth.mockReturnValue({
    can: (p: string) => permissions.includes(p),
    status,
  });

  return render(
    <MantineProvider>
      <MemoryRouter
        initialEntries={[path]}
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <Routes>
          <Route path="/login" element={<div data-testid="login-page">Login Page</div>} />
          <Route
            path="/*"
            element={
              <RequireAuth>
                <ComplaintsRoutes />
              </RequireAuth>
            }
          />
        </Routes>
      </MemoryRouter>
    </MantineProvider>,
  );
}

describe("CMS Client Routes & Guards", () => {
  describe("Default & Public / Citizen Routes", () => {
    it("redirects root path '/' to '/mine'", async () => {
      renderAt("/", []);
      expect(await screen.findByTestId("page-mine")).toBeInTheDocument();
    });

    it("allows any citizen to view 'mine' route without office permissions", async () => {
      renderAt("/mine", []);
      expect(await screen.findByTestId("page-mine")).toBeInTheDocument();
    });

    it("allows any citizen to view 'announcements' route without office permissions", async () => {
      renderAt("/announcements", []);
      expect(await screen.findByTestId("page-announcements")).toBeInTheDocument();
    });
  });

  describe("Office Routes - Unauthorized Access", () => {
    it("blocks '/queue' without complaints.complaint.assign and shows NotPermitted", async () => {
      renderAt("/queue", ["complaints.complaint.view_self"]);
      expect(await screen.findByText("Not available to your role")).toBeInTheDocument();
      expect(screen.queryByTestId("page-queue")).toBeNull();
    });

    it("blocks '/supervisor' without complaints.complaint.supervise", async () => {
      renderAt("/supervisor", ["complaints.complaint.assign"]);
      expect(await screen.findByText("Not available to your role")).toBeInTheDocument();
      expect(screen.queryByTestId("page-supervisor")).toBeNull();
    });

    it("blocks '/reports' without complaints.complaint.report", async () => {
      renderAt("/reports", ["complaints.complaint.assign"]);
      expect(await screen.findByText("Not available to your role")).toBeInTheDocument();
      expect(screen.queryByTestId("page-reports")).toBeNull();
    });

    it("blocks '/roles' without complaints.role.manage", async () => {
      renderAt("/roles", ["complaints.complaint.report"]);
      expect(await screen.findByText("Not available to your role")).toBeInTheDocument();
      expect(screen.queryByTestId("page-roles")).toBeNull();
    });

    it("blocks unauthorized roles with unknown/unsupported permissions", async () => {
      renderAt("/roles", ["unknown.permission", "dummy.role"]);
      expect(await screen.findByText("Not available to your role")).toBeInTheDocument();
      expect(screen.queryByTestId("page-roles")).toBeNull();
    });
  });

  describe("Office Routes - Authorized Access", () => {
    it("renders '/queue' when complaints.complaint.assign is held", async () => {
      renderAt("/queue", ["complaints.complaint.assign"]);
      expect(await screen.findByTestId("page-queue")).toBeInTheDocument();
      expect(screen.queryByText("Not available to your role")).toBeNull();
    });

    it("renders '/supervisor' when complaints.complaint.supervise is held", async () => {
      renderAt("/supervisor", ["complaints.complaint.supervise"]);
      expect(await screen.findByTestId("page-supervisor")).toBeInTheDocument();
      expect(screen.queryByText("Not available to your role")).toBeNull();
    });

    it("renders '/reports' when complaints.complaint.report is held", async () => {
      renderAt("/reports", ["complaints.complaint.report"]);
      expect(await screen.findByTestId("page-reports")).toBeInTheDocument();
      expect(screen.queryByText("Not available to your role")).toBeNull();
    });

    it("renders '/roles' when complaints.role.manage is held", async () => {
      renderAt("/roles", ["complaints.role.manage"]);
      expect(await screen.findByTestId("page-roles")).toBeInTheDocument();
      expect(screen.queryByText("Not available to your role")).toBeNull();
    });
  });

  describe("Unauthenticated Access with RequireAuth Guard", () => {
    it("redirects unauthenticated users to '/login' when wrapped in RequireAuth", async () => {
      renderAt("/queue", [], "anonymous");
      expect(await screen.findByTestId("login-page")).toBeInTheDocument();
      expect(screen.queryByTestId("page-queue")).toBeNull();
      expect(screen.queryByText("Not available to your role")).toBeNull();
    });
  });
});
