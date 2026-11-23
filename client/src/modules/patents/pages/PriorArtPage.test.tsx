import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import PriorArtPage from "./PriorArtPage";

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

describe("PriorArtPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders query input and search button", () => {
    renderWithClient(<PriorArtPage />);

    expect(screen.getByLabelText(/Search Query/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Search Prior Art" })).toBeInTheDocument();
  });

  it("renders search results on search submission", async () => {
    vi.spyOn(http, "post").mockResolvedValueOnce({
      data: {
        query: "solar cell",
        results: ["US123456 - High Efficiency Perovskite Cell"],
      },
    });

    renderWithClient(<PriorArtPage />);

    fireEvent.change(screen.getByLabelText(/Search Query/i), {
      target: { value: "solar cell" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Search Prior Art" }));

    await waitFor(() => {
      expect(screen.getByText("US123456 - High Efficiency Perovskite Cell")).toBeInTheDocument();
    });
  });

  it("renders empty state when search finds no matches", async () => {
    vi.spyOn(http, "post").mockResolvedValueOnce({
      data: {
        query: "nonexistent invention term",
        results: [],
      },
    });

    renderWithClient(<PriorArtPage />);

    fireEvent.change(screen.getByLabelText(/Search Query/i), {
      target: { value: "nonexistent invention term" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Search Prior Art" }));

    await waitFor(() => {
      expect(screen.getByText("No results found")).toBeInTheDocument();
    });
  });
});
