/** My Profile: the portal record, the structured resume and the documents. */
import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { CandidateRecord } from "../api/types";
import ProfilePage from "./ProfilePage";

const hooks = vi.hoisted(() => ({
  useMyProfile: vi.fn(),
  useMyDocuments: vi.fn(),
  useAttachDocument: vi.fn(),
  useDeleteDocument: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

const profile: CandidateRecord = {
  user_id: 1, name: "Asha Verma", roll_no: "23BCS001", email: "asha@example.test",
  programme: "B.Tech", discipline: "CSE", batch_year: 2023,
  resume_link: "https://drive.example/cv", profile_completed: true,
  academic: { cpi: "8.20", semester: 6 },
};
const attach = vi.fn();

function page() {
  return render(<MantineProvider><ProfilePage /></MantineProvider>);
}

describe("ProfilePage", () => {
  beforeEach(() => {
    attach.mockReset();
    hooks.useMyProfile.mockReturnValue({ data: profile, isPending: false, error: null });
    hooks.useMyDocuments.mockReturnValue(
      { data: { results: [] }, isPending: false, error: null });
    hooks.useAttachDocument.mockReturnValue(
      { mutate: attach, isPending: false, isError: false });
    hooks.useDeleteDocument.mockReturnValue({ mutate: vi.fn(), isPending: false });
  });

  it("shows loading", () => {
    hooks.useMyProfile.mockReturnValue({ data: undefined, isPending: true, error: null });
    page();
    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });

  it("renders a real error", () => {
    hooks.useMyProfile.mockReturnValue(
      { data: undefined, isPending: false, error: new Error("boom") });
    page();
    expect(screen.queryByText("My Profile")).not.toBeInTheDocument();
  });

  it("builds the structured resume from the profile", () => {
    page();
    expect(screen.getByText("Structured resume")).toBeInTheDocument();
    expect(screen.getByText(/CPI 8.20/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /resume you keep/ }))
      .toHaveAttribute("href", "https://drive.example/cv");
  });

  it("explains the empty document list", () => {
    page();
    expect(screen.getByText("No documents yet")).toBeInTheDocument();
  });

  it("warns when the portal profile is incomplete", () => {
    hooks.useMyProfile.mockReturnValue(
      { data: { ...profile, profile_completed: false }, isPending: false, error: null });
    page();
    expect(screen.getByText("Your profile is not complete")).toBeInTheDocument();
  });

  it("adds a document only once a link is given", async () => {
    page();
    fireEvent.click(screen.getByRole("button", { name: "Add document" }));
    const dialog = await screen.findByRole("dialog");
    const add = within(dialog).getByRole("button", { name: "Add document" });
    expect(add).toBeDisabled();
    fireEvent.change(screen.getByLabelText(/Drive link/),
      { target: { value: "https://drive.google.com/file/d/x/view" } });
    fireEvent.click(add);
    expect(attach).toHaveBeenCalledWith(
      expect.objectContaining({ kind: "certificate" }), expect.anything());
  });
});
