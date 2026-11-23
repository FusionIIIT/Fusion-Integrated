import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { authAs, mockHttp, renderPage, serverError } from "../test-utils";
import PriorArtPage from "./PriorArtPage";

const auth = vi.hoisted(() => ({ useAuth: vi.fn() }));
vi.mock("../../../auth/AuthProvider", () => auth);

const PERMS = ["pms.prior_art.create"];
const RESULT = { search_id: 3, terms: ["graphene"], suggested_keywords: ["anode"],
  classification_codes: [], suggested_classifications: [],
  sources: [{ code: "patent_databases", label: "Patent databases", status: "not connected" }],
  results: [] as unknown[] };

async function search() {
  await userEvent.type(screen.getByRole("textbox", { name: "Search terms" }), "graphene");
  await userEvent.click(screen.getByRole("button", { name: "Search" }));
}

describe("PriorArtPage", () => {
  afterEach(() => vi.restoreAllMocks());

  it("shows a spinner while searching", async () => {
    authAs(auth.useAuth, PERMS);
    mockHttp({}, { "prior-art/searches": "pending" });
    renderPage(<PriorArtPage />);
    await search();
    await waitFor(() => expect(screen.getByRole("button", { name: "Search" }))
      .toHaveAttribute("data-loading", "true"));
  });

  it("says when nothing recorded matches, and that outside sources were not searched", async () => {
    authAs(auth.useAuth, PERMS);
    mockHttp({}, { "prior-art/searches": RESULT });
    renderPage(<PriorArtPage />);
    await search();
    expect(await screen.findByText("No recorded references match")).toBeInTheDocument();
    expect(screen.getByText("Patent databases: not connected")).toBeInTheDocument();
  });

  it("shows the server's message when the search fails", async () => {
    authAs(auth.useAuth, PERMS);
    mockHttp({}, { "prior-art/searches": serverError(500, "Search unavailable.") });
    renderPage(<PriorArtPage />);
    await search();
    expect(await screen.findByText("Search unavailable.")).toBeInTheDocument();
  });

  it("lists ranked results", async () => {
    authAs(auth.useAuth, PERMS);
    mockHttp({}, { "prior-art/searches": { ...RESULT, results: [{ score: 4, reference: {
      id: 1, application_id: 7, kind: "patent", title: "Graphene coating", identifier: "US1",
      url: "", source_name: "", notes: "", created_at: "" } }] } });
    renderPage(<PriorArtPage />);
    await search();
    expect(await screen.findByText("Graphene coating")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Search" })).toBeEnabled();
  });

  it("attaches a reference", async () => {
    authAs(auth.useAuth, PERMS);
    const calls = mockHttp({ applications: { next: null, previous: null, results: [{ id: 7,
      reference: "PMS-2026-00007", title: "Graphene anode", status: "draft" }] } },
    { "applications/7/prior-art": serverError(409,
      "That reference is already attached to this application.") });
    renderPage(<PriorArtPage />);
    await userEvent.click(screen.getByRole("button", { name: "Attach a reference" }));
    await userEvent.click(screen.getByRole("textbox", { name: "Application" }));
    await userEvent.click(await screen.findByRole("option", { name: /Graphene anode/,
      hidden: true }));
    await userEvent.click(screen.getByRole("textbox", { name: "Kind" }));
    await userEvent.click(await screen.findByRole("option", { name: "Patent", hidden: true }));
    await userEvent.type(screen.getByRole("textbox", { name: "Title" }), "Coating");
    await userEvent.click(screen.getByRole("button", { name: "Attach" }));
    await waitFor(() => expect(calls.post).toHaveBeenCalledWith("/pms/applications/7/prior-art",
      expect.objectContaining({ kind: "patent", title: "Coating" })));
    expect(await screen.findByText(/already attached/)).toBeInTheDocument();
  });
});
