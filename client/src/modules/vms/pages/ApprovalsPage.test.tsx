import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { apiError, renderPage, respondPost, routeGet } from "../test-utils";
import ApprovalsPage from "./ApprovalsPage";

vi.mock("../../../auth/AuthProvider", () => ({ useAuth: () => ({ can: () => true }) }));

const request = (id: number, over: Record<string, unknown> = {}) => ({
  id, visitor_name: `Visitor ${id}`, host_user_id: 1, purpose: "Interview",
  scheduled_start: "2026-01-05T09:30:00", scheduled_end: "2026-01-05T11:00:00",
  status: "pending", source: "pre_registered", is_urgent: false, requested_zones: [],
  decision_note: "", decided_at: null, expires_at: "2026-01-06T09:00:00",
  created_at: "2026-01-04T09:00:00", ...over,
});

function load(results: unknown[], next: string | null = null) {
  return routeGet({ "/vms/host/requests": { results, next, previous: null } });
}

describe("ApprovalsPage", () => {
  it("lists the requests waiting for the host, marking urgent ones", async () => {
    load([request(1), request(2, { is_urgent: true })]);
    renderPage(<ApprovalsPage />);
    expect(await screen.findByText("Visitor 1")).toBeInTheDocument();
    expect(screen.getByText("Visitor 2")).toBeInTheDocument();
    expect(screen.getByText("urgent")).toBeInTheDocument();
    expect(screen.getAllByText("Interview")).toHaveLength(2);
  });

  it("says plainly when nothing is waiting", async () => {
    load([]);
    renderPage(<ApprovalsPage />);
    expect(await screen.findByText("Nothing waiting for you")).toBeInTheDocument();
  });

  it("approves a request with one click and confirms the pass was issued", async () => {
    load([request(7)]);
    const post = respondPost({ id: 1 });
    renderPage(<ApprovalsPage />);
    await userEvent.click(await screen.findByRole("button", { name: /approve/i }));
    await waitFor(() => expect(post).toHaveBeenCalledWith(
      "/vms/host/requests/7/decision", { decision: "approve", note: "" }));
    expect(await screen.findByText(/Approved Visitor 7/)).toBeInTheDocument();
  });

  it("will not reject without a reason, then sends it", async () => {
    load([request(9)]);
    const post = respondPost({});
    renderPage(<ApprovalsPage />);
    await userEvent.click(await screen.findByRole("button", { name: /reject/i }));

    const dialog = await screen.findByRole("dialog");
    const submit = within(dialog).getByRole("button", { name: "Reject" });
    expect(submit).toBeDisabled();
    expect(within(dialog).getByText("A reason is required to reject.")).toBeInTheDocument();

    await userEvent.type(within(dialog).getByLabelText(/reason/i), "Not expected");
    expect(submit).toBeEnabled();
    await userEvent.click(submit);
    await waitFor(() => expect(post).toHaveBeenCalledWith(
      "/vms/host/requests/9/decision", { decision: "reject", note: "Not expected" }));
  });

  it("approves several selected requests in one call and reports partial failure", async () => {
    load([request(1), request(2), request(3)]);
    const post = respondPost({ results: [
      { id: 1, ok: true }, { id: 2, ok: true }, { id: 3, ok: false, error: "expired" }] });
    renderPage(<ApprovalsPage />);
    await screen.findByText("Visitor 1");
    const boxes = screen.getAllByRole("checkbox");
    await userEvent.click(boxes[1]!);
    await userEvent.click(boxes[2]!);
    await userEvent.click(boxes[3]!);
    await userEvent.click(screen.getByRole("button", { name: /approve 3 selected/i }));
    await waitFor(() => expect(post).toHaveBeenCalledWith(
      "/vms/host/requests/bulk-decision", { ids: [1, 2, 3], decision: "approve", note: "" }));
    expect(await screen.findByText(/Approved 2; 1 could not be approved/)).toBeInTheDocument();
  });

  it("tells the host when more requests are waiting beyond this page", async () => {
    load([request(1)], "https://x/next");
    renderPage(<ApprovalsPage />);
    expect(await screen.findByText(/More requests are waiting/)).toBeInTheDocument();
  });

  it("shows the server's message when the list cannot be loaded", async () => {
    vi.spyOn((await import("../../../lib/http")).http, "get")
      .mockRejectedValue(apiError(500, "The directory is down."));
    renderPage(<ApprovalsPage />);
    expect(await screen.findByText("The directory is down.")).toBeInTheDocument();
  });
});
