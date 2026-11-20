/** StudentCpiPage: loading, error, empty, data. */
import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import StudentCpiPage from "./StudentCpiPage";

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

const EMPTY = {"count": 0, "limit": 50, "offset": 0, "results": []};
const DATA = {"count": 1, "limit": 50, "offset": 0, "results": [{"user_id": 4021, "roll_no": "23BCS001", "name": "Asha Verma", "discipline": "CSE", "programme": "B.Tech", "batch_year": 2023, "cpi": "8.10", "earned_credits": "120", "active_backlogs": 0, "semester": 6, "semester_type": "Even Semester", "synced_at": null}]};

function query(over: Record<string, unknown>) {
  return { data: undefined, isPending: false, error: null, ...over };
}

function page() {
  return render(
    <MantineProvider><MemoryRouter><StudentCpiPage /></MemoryRouter></MantineProvider>);
}

describe("StudentCpiPage", () => {
  beforeEach(() => {
    for (const fn of Object.values(hooks)) {
      fn.mockReturnValue({ ...query({ data: EMPTY }), mutate: vi.fn(), variables: undefined });
    }
    hooks.useSeasons.mockReturnValue(query({ data: [] }));
  });

  it("shows nothing stale while loading", () => {
    hooks.useCpiDirectory.mockReturnValue(query({ isPending: true }));
    page();
    expect(screen.queryByText("Asha Verma")).not.toBeInTheDocument();
  });

  it("renders a real error", () => {
    hooks.useCpiDirectory.mockReturnValue(query({ error: new Error("boom") }));
    page();
    expect(screen.getByText("Could not load this")).toBeInTheDocument();
  });

  it("says what an empty list means", () => {
    page();
    expect(screen.getByText("No students match these filters")).toBeInTheDocument();
  });

  it("renders the data", () => {
    hooks.useCpiDirectory.mockReturnValue(query({ data: DATA }));
    page();
    expect(screen.getAllByText("Asha Verma").length).toBeGreaterThan(0);
  });
});
