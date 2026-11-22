import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import NewApplicationPage from "./NewApplicationPage";

function renderWithClient(ui: ReactNode) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MantineProvider>
        <MemoryRouter>{ui}</MemoryRouter>
      </MantineProvider>
    </QueryClientProvider>,
  );
}

describe("NewApplicationPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders all required form controls with accessible labels", () => {
    renderWithClient(<NewApplicationPage />);

    expect(screen.getByLabelText(/Invention Title/i)).toBeInTheDocument();
    expect(screen.getAllByLabelText(/Domain Category/i)[0]).toBeInTheDocument();
    expect(screen.getAllByLabelText(/Jurisdiction/i)[0]).toBeInTheDocument();
    expect(screen.getByLabelText(/Abstract/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Detailed Technical Description/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Patent Claims/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Submit Application/i })).toBeInTheDocument();
  });

  it("submits application payload when form is filled and submitted", async () => {
    const postSpy = vi.spyOn(http, "post").mockResolvedValueOnce({
      data: { id: 10, title: "Quantum Sensor" },
    });

    renderWithClient(<NewApplicationPage />);

    fireEvent.change(screen.getByLabelText(/Invention Title/i), {
      target: { value: "Quantum Sensor" },
    });
    fireEvent.change(screen.getByLabelText(/Abstract/i), {
      target: { value: "A high-precision quantum sensor." },
    });
    fireEvent.change(screen.getByLabelText(/Detailed Technical Description/i), {
      target: { value: "Detailed quantum implementation description." },
    });
    fireEvent.change(screen.getByLabelText(/Patent Claims/i), {
      target: { value: "1. A quantum sensor system comprising..." },
    });

    fireEvent.click(screen.getByRole("button", { name: /Submit Application/i }));

    await waitFor(() => {
      expect(postSpy).toHaveBeenCalledWith(
        "/patents/applications",
        expect.objectContaining({
          title: "Quantum Sensor",
          abstract: "A high-precision quantum sensor.",
          description: "Detailed quantum implementation description.",
          claims: "1. A quantum sensor system comprising...",
        }),
      );
    });
  });
});
