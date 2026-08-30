/** Every page renders.
 *
 *  The hooks were tested and the types checked, but nothing had ever executed
 *  a component — a bad Mantine prop or a null dereference in a cell renderer
 *  typechecks fine and throws on mount. Each page is rendered twice: empty,
 *  which is what a new deployment looks like, and populated, which is the path
 *  the cell renderers actually run on.
 */
import { MantineProvider } from "@mantine/core";
import { Notifications } from "@mantine/notifications";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import ApplyPage from "./ApplyPage";
import BalancesPage from "./BalancesPage";
import MyLeavePage from "./MyLeavePage";
import PolicyPage from "./PolicyPage";
import ResumptionsPage from "./ResumptionsPage";
import ReviewQueuePage from "./ReviewQueuePage";
import RoutingQueuePage from "./RoutingQueuePage";
import SanctionQueuePage from "./SanctionQueuePage";
import SubstitutePage from "./SubstitutePage";

const REQUEST = {
  id: 1, user_id: 501, category: "CL", state: "AWAITING_UNIT_HEAD",
  starts_on: "2026-03-02", ends_on: "2026-03-03", half: "",
  reason: "Personal work", requested_days: "2.00", actual_days: null,
  station_leave: false, station_destination: "", resumed_on: null,
  decided_at: null, created_at: "2026-03-01T10:00:00Z",
};
const BALANCE = {
  category: "CL", available: "6.00", credited: "8.00",
  consumed: "2.00", restored: "0.00",
};
const POLICY = {
  id: 1, version: "2026.1", effective_from: "2026-01-01", effective_to: null,
  published: true, note: "", vl_to_el_ratio: "2.00",
  vl_to_el_rounding: "EXACT_HALF", early_return_tail: "TRIM_TO_LAST_WORKING_DAY",
};
const CALENDAR = { id: 1, year: 2026, version: "1", published: true };

/** One shape per URL, so a page that fetches several lists gets sane data for
 *  each rather than the same array everywhere. */
function respond(url: string, populated: boolean) {
  if (!populated) return { data: [] };
  if (url.includes("balances") || url.includes("me/balances")) return { data: [BALANCE] };
  if (url.includes("admin/policies")) return { data: [POLICY] };
  if (url.includes("admin/calendars")) return { data: [CALENDAR] };
  if (url.includes("statement")) return { data: [] };
  return { data: [REQUEST] };
}

function Wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return (
    <MantineProvider>
      <QueryClientProvider client={qc}>
        <MemoryRouter future={{ v7_startTransition: true,
                                v7_relativeSplatPath: true }}>
          <Notifications />
          {children}
        </MemoryRouter>
      </QueryClientProvider>
    </MantineProvider>
  );
}

const PAGES: [string, () => JSX.Element, RegExp][] = [
  ["My Leave", MyLeavePage, /my leave/i],
  ["Apply", ApplyPage, /apply for leave/i],
  ["Standing In", SubstitutePage, /standing in/i],
  ["Review Queue", ReviewQueuePage, /review queue/i],
  ["Routing Queue", RoutingQueuePage, /routing queue/i],
  ["Sanction Queue", SanctionQueuePage, /sanction queue/i],
  ["Resumptions", ResumptionsPage, /resumptions/i],
  ["Balances", BalancesPage, /balances/i],
  ["Policy & Calendar", PolicyPage, /policy & calendar/i],
];

describe("leave pages", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it.each(PAGES)("%s renders with nothing to show", async (_name, Page, heading) => {
    vi.spyOn(http, "get").mockImplementation(async (url: string) =>
      respond(url, false) as never);

    render(<Wrapper><Page /></Wrapper>);

    expect(await screen.findByText(heading)).toBeInTheDocument();
  });

  it.each(PAGES)("%s renders with data", async (_name, Page, heading) => {
    vi.spyOn(http, "get").mockImplementation(async (url: string) =>
      respond(url, true) as never);

    render(<Wrapper><Page /></Wrapper>);

    await waitFor(() => expect(screen.getByText(heading)).toBeInTheDocument());
  });

  it("shows a real empty state rather than a blank table", async () => {
    vi.spyOn(http, "get").mockImplementation(async () => ({ data: [] }) as never);

    render(<Wrapper><ReviewQueuePage /></Wrapper>);

    expect(await screen.findByText(/nothing is waiting on you/i)).toBeInTheDocument();
  });

  it("renders the charged days beside the period, not just the dates", async () => {
    vi.spyOn(http, "get").mockImplementation(async (url: string) =>
      respond(url, true) as never);

    render(<Wrapper><ReviewQueuePage /></Wrapper>);

    expect(await screen.findByText(/2 days charged/i)).toBeInTheDocument();
  });
});
