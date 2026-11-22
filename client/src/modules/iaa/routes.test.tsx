/** A role without a page's permission gets NotPermitted and the page never mounts; a role
 *  with it gets the page. Removing or changing a guard in routes.tsx fails here. */
import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { Suspense } from "react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { routes } from "./routes";

const auth = vi.hoisted(() => ({ useAuth: vi.fn() }));
vi.mock("../../auth/AuthProvider", () => auth);

const mounted = vi.hoisted(() => vi.fn());
vi.mock("./pages/MyRequestsPage", () => ({ default: () => (mounted("my-requests"), <p>page my-requests</p>) }));
vi.mock("./pages/FinanceReviewPage", () => ({ default: () => (mounted("finance"), <p>page finance</p>) }));
vi.mock("./pages/ApprovalsPage", () => ({ default: () => (mounted("approvals"), <p>page approvals</p>) }));
vi.mock("./pages/AnomaliesPage", () => ({ default: () => (mounted("anomalies"), <p>page anomalies</p>) }));
vi.mock("./pages/ObservationsPage", () => ({ default: () => (mounted("observations"), <p>page observations</p>) }));
vi.mock("./pages/ReportsPage", () => ({ default: () => (mounted("reports"), <p>page reports</p>) }));
vi.mock("./pages/NotificationsPage", () => ({ default: () => (mounted("notifications"), <p>page notifications</p>) }));
vi.mock("./pages/ConfigurationPage", () => ({ default: () => (mounted("configuration"), <p>page configuration</p>) }));

// Each page and the one permission its nav item requires (registry.py).
const PAGES: [string, string][] = [
  ["my-requests", "iaa.request.create"],
  ["finance", "iaa.request.review"],
  ["approvals", "iaa.request.approve"],
  ["anomalies", "iaa.anomaly.view"],
  ["observations", "iaa.observation.view"],
  ["reports", "iaa.report.view"],
  ["notifications", "iaa.notification.view"],
  ["configuration", "iaa.configuration.view"],
];

function visit(path: string, permissions: string[]) {
  auth.useAuth.mockReturnValue({ can: (p: string) => permissions.includes(p) });
  const router = createMemoryRouter(routes, { initialEntries: [`/${path}`] });
  return render(
    <MantineProvider>
      <Suspense fallback={<p>loading</p>}><RouterProvider router={router} /></Suspense>
    </MantineProvider>,
  );
}

beforeEach(() => mounted.mockClear());

describe("IAA route guards", () => {
  it.each(PAGES)("%s refuses a role that lacks %s and never mounts the page", async (path, code) => {
    const others = PAGES.map(([, c]) => c).filter((c) => c !== code);
    visit(path, others);
    expect(await screen.findByText("Not available to your role")).toBeInTheDocument();
    expect(screen.queryByText(`page ${path}`)).toBeNull();
    expect(mounted).not.toHaveBeenCalled();
  });

  it.each(PAGES)("%s opens for a role holding %s", async (path, code) => {
    visit(path, [code]);
    expect(await screen.findByText(`page ${path}`)).toBeInTheDocument();
    expect(screen.queryByText("Not available to your role")).toBeNull();
  });

  it("sends the module's index to the notifications page", async () => {
    visit("", ["iaa.notification.view"]);
    expect(await screen.findByText("page notifications")).toBeInTheDocument();
  });

  it("guards every page it routes to", () => {
    const paths = routes.map((r) => r.path).filter(Boolean).sort();
    expect(paths).toEqual(PAGES.map(([p]) => p).sort());
  });
});
