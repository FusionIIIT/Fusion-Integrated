import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import CreateFilePage from "./CreateFilePage";

function renderWithProviders(ui: ReactNode) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <MantineProvider>
      <QueryClientProvider client={qc}>
        <MemoryRouter>{ui}</MemoryRouter>
      </QueryClientProvider>
    </MantineProvider>
  );
}

describe("CreateFilePage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders form inputs with visible labels", () => {
    renderWithProviders(<CreateFilePage />);
    expect(screen.getByLabelText(/File Subject/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Initial Note \/ Description/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Save as draft/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Recipient Employee ID/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Circulate File" })).toBeInTheDocument();
  });

  it("switches to draft mode when the draft checkbox is checked", () => {
    renderWithProviders(<CreateFilePage />);
    const draftCheckbox = screen.getByLabelText(/Save as draft/i);
    fireEvent.click(draftCheckbox);

    expect(screen.queryByLabelText(/Recipient Employee ID/i)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save Draft" })).toBeInTheDocument();
  });

  it("prevents submission when required fields are missing", async () => {
    const postSpy = vi.spyOn(http, "post");
    renderWithProviders(<CreateFilePage />);
    const submitBtn = screen.getByRole("button", { name: "Circulate File" });
    fireEvent.click(submitBtn);

    expect(postSpy).not.toHaveBeenCalled();
  });

  it("submits the form successfully and triggers API call", async () => {
    vi.spyOn(http, "post").mockResolvedValue({
      data: {
        id: 103,
        file_number: "FTS-2026-0003",
        subject: "New Curriculum Review",
        status: "CIRCULATING",
      },
    });

    renderWithProviders(<CreateFilePage />);
    fireEvent.change(screen.getByLabelText(/File Subject/i), {
      target: { value: "New Curriculum Review" },
    });
    fireEvent.change(screen.getByLabelText(/Initial Note \/ Description/i), {
      target: { value: "Review draft attached." },
    });
    fireEvent.change(screen.getByLabelText(/Recipient Employee ID/i), {
      target: { value: "5" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Circulate File" }));

    await waitFor(() => {
      expect(http.post).toHaveBeenCalledWith("/api/v1/filetracking/files/", {
        subject: "New Curriculum Review",
        initial_comment: "Review draft attached.",
        is_draft: false,
        recipient_user_id: 5,
        recipient_designation: "",
      });
    });
  });
});
