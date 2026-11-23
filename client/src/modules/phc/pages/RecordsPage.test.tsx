import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import RecordsPage from "./RecordsPage";
import { listStateTests, refusal, renderPage, state } from "./testing";

const http = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), put: vi.fn() }));
vi.mock("../../../lib/http", async (orig) => ({
  ...(await orig<typeof import("../../../lib/http")>()), http,
}));
vi.mock("../../../auth/AuthProvider", () => ({
  useAuth: () => ({ can: (p: string) => state.permissions.has(p) }),
}));

const visits = { next: null, previous: null, results: [{
  id: 11, patient_user_id: 4021, visit_date: "2026-11-21", complaint: "Fever",
  diagnosis: "Viral fever", created_at: "2026-11-21T10:00:00Z",
  prescriptions: [{ id: 17, medicine: "Paracetamol 500mg", dosage: "1-0-1",
    duration_days: 3, instructions: "" }] }] };

describe("RecordsPage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    state.permissions = new Set(["phc.record.view"]);
  });

  listStateTests({ get: http.get, page: () => <RecordsPage />,
    empty: { results: [], next: null, previous: null }, emptyText: /no medical records/i });

  it("is read-only for a patient", async () => {
    http.get.mockResolvedValue({ data: visits });
    renderPage(<RecordsPage />);
    expect(await screen.findByText(/paracetamol 500mg/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /record visit/i })).not.toBeInTheDocument();
  });

  it("downloads the selected records and shows a refusal", async () => {
    http.get.mockImplementation((url: string) => url === "/phc/records/pdf"
      ? Promise.reject(refusal("One of those records does not exist.", 404))
      : Promise.resolve({ data: visits }));
    renderPage(<RecordsPage />);
    const download = await screen.findByRole("button", { name: /download pdf/i });
    expect(download).toBeDisabled();
    fireEvent.click(await screen.findByLabelText(/visit on 2026-11-21/i));
    fireEvent.click(download);
    expect(await screen.findByText("One of those records does not exist.")).toBeInTheDocument();
    expect(http.get).toHaveBeenCalledWith("/phc/records/pdf",
      { params: { ids: "11" }, responseType: "blob" });
  });

  it("gives PHC staff the record-visit form", async () => {
    state.permissions.add("phc.record.create");
    http.get.mockResolvedValue({ data: visits });
    renderPage(<RecordsPage />);
    fireEvent.click(await screen.findByRole("button", { name: /record visit/i }));
    expect(await screen.findByLabelText(/search patient/i)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: /save visit/i }))
      .toBeDisabled());
  });
});
