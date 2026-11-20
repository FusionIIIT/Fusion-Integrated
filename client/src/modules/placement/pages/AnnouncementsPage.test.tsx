/** AnnouncementsPage: loading, error, empty, data, and the permission gate. */
import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AnnouncementsPage from "./AnnouncementsPage";

const hooks = vi.hoisted(() => ({
  useAddCandidates: vi.fn(),
  useAnnouncements: vi.fn(),
  useApplicationHistory: vi.fn(),
  useApplications: vi.fn(),
  useApply: vi.fn(),
  useApproveLate: vi.fn(),
  useAttachDocument: vi.fn(),
  useBulkTransition: vi.fn(),
  useCompanies: vi.fn(),
  useCompanyDecision: vi.fn(),
  useCorrectRecord: vi.fn(),
  useCpiDirectory: vi.fn(),
  useCpiFilters: vi.fn(),
  useCreatePosting: vi.fn(),
  useCsvExport: vi.fn(),
  useDeclareNotJoining: vi.fn(),
  useDeleteDocument: vi.fn(),
  useEligibility: vi.fn(),
  useInviteRecruiter: vi.fn(),
  useIssueOffer: vi.fn(),
  useMyClearance: vi.fn(),
  useMyConductRecord: vi.fn(),
  useMyDocuments: vi.fn(),
  useMyProfile: vi.fn(),
  useMyRecords: vi.fn(),
  useMyRegistrations: vi.fn(),
  useOffers: vi.fn(),
  useOfficeRecords: vi.fn(),
  useOptOut: vi.fn(),
  useOutstandingLetters: vi.fn(),
  usePosting: vi.fn(),
  usePostings: vi.fn(),
  usePublishAnnouncement: vi.fn(),
  usePublishPosting: vi.fn(),
  useReRegister: vi.fn(),
  useRecordRevisions: vi.fn(),
  useRegister: vi.fn(),
  useRegisterCompany: vi.fn(),
  useRegistrationTerms: vi.fn(),
  useRespondToOffer: vi.fn(),
  useRounds: vi.fn(),
  useScheduleRound: vi.fn(),
  useSeasons: vi.fn(),
  useStats: vi.fn(),
  useStatsTrends: vi.fn(),
  useSubmitOfferLetter: vi.fn(),
  useTransition: vi.fn(),
  useWithdrawAnnouncement: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);
const auth = vi.hoisted(() => ({ can: (_: string): boolean => true }));
vi.mock("../../../auth/AuthProvider", () => ({ useAuth: () => auth }));

const EMPTY = {"results": [], "next": null, "previous": null};
const DATA = {"results": [{"id": 51, "title": "Drive on Monday", "body": "Hall 2.", "topic": "drive", "audience": "students", "placement_year": "2026-27", "published_at": "2026-11-04T10:00:00Z", "published_by_role": "placement officer", "is_withdrawn": false, "withdrawn_reason": "", "created_at": "2026-11-04T10:00:00Z"}], "next": null, "previous": null};

function query(over: Record<string, unknown>) {
  return { data: undefined, isPending: false, error: null, ...over };
}

function page() {
  return render(
    <MantineProvider><MemoryRouter><AnnouncementsPage /></MemoryRouter></MantineProvider>);
}

describe("AnnouncementsPage", () => {
  beforeEach(() => {
    auth.can = () => true;
    for (const fn of Object.values(hooks)) {
      fn.mockReturnValue({ ...query({ data: EMPTY }), mutate: vi.fn(), variables: undefined });
    }
    hooks.useSeasons.mockReturnValue(query({ data: [] }));
  });

  it("shows nothing stale while loading", () => {
    hooks.useAnnouncements.mockReturnValue(query({ isPending: true }));
    page();
    expect(screen.queryByText("Drive on Monday")).not.toBeInTheDocument();
  });

  it("renders a real error", () => {
    hooks.useAnnouncements.mockReturnValue(query({ error: new Error("boom") }));
    page();
    expect(screen.getByText("Could not load this")).toBeInTheDocument();
  });

  it("says what an empty list means", () => {
    page();
    expect(screen.getByText("Nothing announced yet")).toBeInTheDocument();
  });

  it("renders the data", () => {
    hooks.useAnnouncements.mockReturnValue(query({ data: DATA }));
    page();
    expect(screen.getAllByText("Drive on Monday").length).toBeGreaterThan(0);
  });

  it("hides 'Publish' from a role without the permission", () => {
    auth.can = () => false;
    page();
    expect(screen.queryByRole("button", { name: "Publish" })).not.toBeInTheDocument();
  });

  it("offers 'Publish' to a role with it", () => {
    page();
    expect(screen.getByRole("button", { name: "Publish" })).toBeInTheDocument();
  });
});
