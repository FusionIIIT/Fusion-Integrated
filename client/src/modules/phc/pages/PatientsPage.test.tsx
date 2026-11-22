import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useAuth } from "../../../auth/AuthProvider";
import { usePatients, usePhcPost } from "../api";
import PatientsPage from "./PatientsPage";

vi.mock("../../../auth/AuthProvider", () => ({ useAuth: vi.fn() }));
vi.mock("../api", () => ({ usePatients: vi.fn(), usePhcPost: vi.fn() }));

const patients = vi.mocked(usePatients);
const post = vi.mocked(usePhcPost);
const auth = vi.mocked(useAuth);
const mutateAsync = vi.fn();

function renderPage() {
  return render(<MantineProvider><PatientsPage /></MantineProvider>);
}

describe("PatientsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    auth.mockReturnValue({
      can: (permission: string) => permission === "phc.patient.register_self",
      session: { user: { id: 1001 } },
    } as unknown as ReturnType<typeof useAuth>);
    post.mockReturnValue({ mutateAsync, isPending: false } as unknown as ReturnType<typeof usePhcPost>);
  });

  it("renders a distinct loading state", () => {
    patients.mockReturnValue({ data: undefined, isPending: true, error: null } as never);
    renderPage();
    expect(screen.getByText("Loading patients…")).toBeInTheDocument();
  });

  it("renders an empty state", () => {
    patients.mockReturnValue({ data: { results: [] }, isPending: false, error: null } as never);
    renderPage();
    expect(screen.getByText("No patient records yet.")).toBeInTheDocument();
  });

  it("renders the API error state", () => {
    patients.mockReturnValue({
      data: undefined,
      isPending: false,
      error: { response: { data: { error: { message: "Directory unavailable" } } } },
    } as never);
    renderPage();
    expect(screen.getByText("Could not load this")).toBeInTheDocument();
    expect(screen.getByText("Directory unavailable")).toBeInTheDocument();
  });

  it("shows only the returned patient rows and submits self registration", async () => {
    patients.mockReturnValue({
      data: { results: [{ id: 1, user_id: 1001, patient_number: "PHC-00001001",
        created_at: "2026-01-01T00:00:00Z" }] }, isPending: false, error: null,
    } as never);
    mutateAsync.mockResolvedValue({});
    renderPage();
    expect(screen.getByText("PHC-00001001")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Register patient" }));
    expect(mutateAsync).toHaveBeenCalledWith({});
  });
});
