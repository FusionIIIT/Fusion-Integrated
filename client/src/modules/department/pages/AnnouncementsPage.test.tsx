import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AnnouncementsPage from "./AnnouncementsPage";
import { api, page, renderPage, serverError, setup } from "./testUtils";

vi.mock("../../../lib/http", async (orig) => (await import("./testUtils")).httpMock(orig));
vi.mock("../../../auth/AuthProvider", async () => (await import("./testUtils")).authMock());

const ANN = { id: 1, department: "CSE", title: "Lab closed", body: "Friday", audience_role: "all",
  programme: "", batch_year: null, status: "active", author_id: 1, published_at: "2026-11-22", edited_at: null };

describe("AnnouncementsPage", () => {
  beforeEach(() => vi.clearAllMocks());

  it("shows loading while the list is pending", () => {
    setup([], { "/announcements": "pending" });
    renderPage(<AnnouncementsPage />);
    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });

  it("shows a real empty state", async () => {
    setup(["department.announcement.view"], { "/announcements": page([]) });
    renderPage(<AnnouncementsPage />);
    expect(await screen.findByText("No announcements for you yet")).toBeInTheDocument();
  });

  it("shows the server's message when the list fails", async () => {
    setup([], { "/announcements": serverError() });
    renderPage(<AnnouncementsPage />);
    expect(await screen.findByText("Server exploded.")).toBeInTheDocument();
  });

  it("hides publishing and maintenance controls from a student", async () => {
    setup(["department.announcement.view"], { "/announcements": page([ANN]) });
    renderPage(<AnnouncementsPage />);
    await screen.findByText("Lab closed");
    expect(screen.queryByRole("button", { name: /publish announcement/i })).toBeNull();
    expect(screen.queryByRole("button", { name: "Edit" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Delete" })).toBeNull();
  });

  it("publishes, and shows the server's refusal as sent", async () => {
    setup(["department.announcement.view", "department.announcement.create"], { "/announcements": page([]) }, "faculty");
    api.post.mockRejectedValueOnce(serverError("Give the announcement a title.", 422));
    renderPage(<AnnouncementsPage />);
    fireEvent.click(await screen.findByRole("button", { name: /publish announcement/i }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.change(within(dialog).getByLabelText("Text"), { target: { value: "Body" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Publish" }));
    expect(await screen.findByText("Give the announcement a title.")).toBeInTheDocument();
    api.post.mockResolvedValueOnce({ data: ANN });
    fireEvent.change(within(dialog).getByLabelText("Title"), { target: { value: "Lab closed" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Publish" }));
    await waitFor(() => expect(api.post).toHaveBeenLastCalledWith("/department/announcements",
      expect.objectContaining({ title: "Lab closed", body: "Body", audience_role: "all" })));
  });

  it("gives the HOD edit, hide and delete", async () => {
    setup(["department.announcement.view", "department.announcement.update", "department.announcement.delete"],
      { "/announcements": page([ANN]) }, "hod");
    api.post.mockResolvedValue({ data: { ...ANN, status: "hidden" } });
    renderPage(<AnnouncementsPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Hide" }));
    await waitFor(() => expect(api.post).toHaveBeenCalledWith("/department/announcements/1/hide"));
    expect(screen.getByRole("button", { name: "Delete" })).toBeInTheDocument();
  });

  it("shows an HOD acting as faculty no HOD controls, though the session holds the permissions", async () => {
    setup(["department.announcement.view", "department.announcement.update", "department.announcement.delete",
      "department.announcement.create"], { "/announcements": page([ANN]) }, "faculty");
    renderPage(<AnnouncementsPage />);
    await screen.findByText("Lab closed");
    expect(await screen.findByRole("button", { name: /publish announcement/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Hide" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Delete" })).toBeNull();
  });

  it("shows the owning office no control its permissions do not allow", async () => {
    setup(["department.announcement.view"], { "/announcements": page([ANN]) }, "hod");
    renderPage(<AnnouncementsPage />);
    expect(await screen.findByText("Lab closed")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Publish announcement" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Edit" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Hide" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Delete" })).toBeNull();
  });

  it("shows the server's refusal when hiding fails", async () => {
    setup(["department.announcement.view", "department.announcement.update", "department.announcement.delete"],
      { "/announcements": page([ANN]) }, "hod");
    api.post.mockRejectedValueOnce(serverError("That announcement is already hidden.", 409));
    renderPage(<AnnouncementsPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Hide" }));
    expect(await screen.findByText("That announcement is already hidden.")).toBeInTheDocument();
  });

  it("shows the server's refusal when deleting fails", async () => {
    setup(["department.announcement.view", "department.announcement.delete"], { "/announcements": page([ANN]) }, "hod");
    api.delete.mockRejectedValueOnce(serverError("That announcement was already deleted.", 409));
    renderPage(<AnnouncementsPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Delete" }));
    expect(await screen.findByText("That announcement was already deleted.")).toBeInTheDocument();
  });
});
