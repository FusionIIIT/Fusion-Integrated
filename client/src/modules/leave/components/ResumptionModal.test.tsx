/** The resumption date is the FIRST DAY BACK, not the last day of leave.
 *
 *  The modal defaulted to the sanctioned end date and refused anything later,
 *  so somebody who finished on the 17th and returned on the 18th could only
 *  report the 17th — which the backend reads as returning a day early, and
 *  hands back days that were used.
 */
import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import { ResumptionModal } from "./ResumptionModal";
import type { LeaveRequest } from "../api/types";

const REQUEST: LeaveRequest = {
  id: 7, user_id: 501, category: "EL", state: "AWAITING_RESUMPTION",
  starts_on: "2026-08-10", ends_on: "2026-08-17", half: "",
  reason: "Family", requested_days: "8.00", actual_days: null,
  station_leave: false, station_destination: "", resumed_on: null,
  decided_at: null, created_at: "2026-08-01T10:00:00Z",
};

function Wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return (
    <MantineProvider>
      <QueryClientProvider client={qc}>{children}</QueryClientProvider>
    </MantineProvider>
  );
}

describe("ResumptionModal", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("asks for the first day back, not the last day of leave", async () => {
    render(
      <Wrapper>
        <ResumptionModal request={REQUEST} onClose={() => undefined} />
      </Wrapper>,
    );

    expect(await screen.findByText(/first day back at work/i)).toBeInTheDocument();
  });

  it("submits the day AFTER the sanctioned end by default", async () => {
    const post = vi.spyOn(http, "post").mockResolvedValue({ data: REQUEST });
    render(
      <Wrapper>
        <ResumptionModal request={REQUEST} onClose={() => undefined} />
      </Wrapper>,
    );

    await userEvent.click(await screen.findByRole("button", { name: /report/i }));

    // Leave ran to the 17th, so a normal return is the 18th. Sending the 17th
    // would be read as an early return.
    await waitFor(() => expect(post).toHaveBeenCalledWith(
      "/leave/requests/7/resumption",
      expect.objectContaining({ resumed_on: "2026-08-18" }),
    ));
  });

  it("explains the default rather than leaving it unexplained", async () => {
    render(
      <Wrapper>
        <ResumptionModal request={REQUEST} onClose={() => undefined} />
      </Wrapper>,
    );

    // Not pinned to a date format: formatDay follows the runtime locale, and
    // asserting one spelling of 17 August would fail on somebody else's machine.
    // The subtitle also mentions the end date, so match the field's own hint.
    expect(await screen.findByText(/normal return is the next working day/i))
      .toBeInTheDocument();
  });

  it("does not warn about an early return on the default", async () => {
    render(
      <Wrapper>
        <ResumptionModal request={REQUEST} onClose={() => undefined} />
      </Wrapper>,
    );

    await screen.findByText(/first day back at work/i);
    expect(screen.queryByText(/before the end of your sanctioned leave/i))
      .not.toBeInTheDocument();
  });
});
