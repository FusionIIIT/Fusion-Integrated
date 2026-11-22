import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import FeedbackPage from "./FeedbackPage";
import { api, page, renderPage, serverError, setup } from "./testUtils";

vi.mock("../../../lib/http", async (orig) => (await import("./testUtils")).httpMock(orig));
vi.mock("../../../auth/AuthProvider", async () => (await import("./testUtils")).authMock());

const FB = { id: 4, subject: "Projector", body: "Broken", category: "", status: "new", submitter_id: 2001,
  submitter_kind: "student", reviewed_at: null, disposed_at: null, resolution_note: "", created_at: "2026-11-22",
  notes: [] };
const STUDENT = ["department.feedback.view", "department.feedback.create"];

describe("FeedbackPage", () => {
  beforeEach(() => vi.clearAllMocks());

  it("shows loading", () => {
    setup(STUDENT, { "/feedback": "pending" });
    renderPage(<FeedbackPage />);
    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });

  it("shows an empty state", async () => {
    setup(STUDENT, { "/feedback": page([]) });
    renderPage(<FeedbackPage />);
    expect(await screen.findByText("No feedback to show")).toBeInTheDocument();
  });

  it("shows the error message", async () => {
    setup(STUDENT, { "/feedback": serverError() });
    renderPage(<FeedbackPage />);
    expect(await screen.findByText("Server exploded.")).toBeInTheDocument();
  });

  it("gives the submitter no review controls", async () => {
    setup(STUDENT, { "/feedback": page([FB]) });
    renderPage(<FeedbackPage />);
    await screen.findByText("Projector");
    expect(screen.queryByRole("button", { name: "Review" })).toBeNull();
  });

  it("submits feedback and shows a refusal", async () => {
    setup(STUDENT, { "/feedback": page([]) });
    api.post.mockRejectedValueOnce(serverError("Give your feedback a subject and some text.", 422));
    renderPage(<FeedbackPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Submit feedback" }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.change(within(dialog).getByLabelText("Subject"), { target: { value: "Projector" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    expect(await screen.findByText("Give your feedback a subject and some text.")).toBeInTheDocument();
    expect(api.post).toHaveBeenCalledWith("/department/feedback", { subject: "Projector", body: "" });
  });

  it("lets Dept_Admin review new feedback", async () => {
    setup(["department.feedback.view", "department.feedback.review"], { "/feedback": page([FB]) });
    api.post.mockResolvedValue({ data: { ...FB, status: "under_review" } });
    renderPage(<FeedbackPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Review" }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    await waitFor(() => expect(api.post).toHaveBeenCalledWith("/department/feedback/4/review",
      { category: "", disposition: "", note: "" }));
  });
});
