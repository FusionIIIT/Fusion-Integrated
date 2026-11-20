/** ReportsPage: loading, error, unpublished, student figures, and the office's extra reports. */
import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ReportsPage from "./ReportsPage";

const hooks = vi.hoisted(() => ({
  usePostings: vi.fn(),
  usePosting: vi.fn(),
  useEligibility: vi.fn(),
  useCreatePosting: vi.fn(),
  usePublishPosting: vi.fn(),
  useApplications: vi.fn(),
  useApply: vi.fn(),
  useTransition: vi.fn(),
  useOffers: vi.fn(),
  useIssueOffer: vi.fn(),
  useRespondToOffer: vi.fn(),
  useCompanies: vi.fn(),
  useRegisterCompany: vi.fn(),
  useCompanyDecision: vi.fn(),
  useInviteRecruiter: vi.fn(),
  useRounds: vi.fn(),
  useScheduleRound: vi.fn(),
  useAddCandidates: vi.fn(),
  useAnnouncements: vi.fn(),
  usePublishAnnouncement: vi.fn(),
  useWithdrawAnnouncement: vi.fn(),
  useStats: vi.fn(),
  useStatsTrends: vi.fn(),
  useMyProfile: vi.fn(),
  useMyDocuments: vi.fn(),
  useAttachDocument: vi.fn(),
  useDeleteDocument: vi.fn(),
  useCsvExport: vi.fn(),
  useApplicationHistory: vi.fn(),
  useMyConductRecord: vi.fn(),
  useBulkTransition: vi.fn(),
  useMyRecords: vi.fn(),
  useMyClearance: vi.fn(),
  useSubmitOfferLetter: vi.fn(),
  useDeclareNotJoining: vi.fn(),
  useOutstandingLetters: vi.fn(),
  useMyRegistrations: vi.fn(),
  useRegistrationTerms: vi.fn(),
  useRegister: vi.fn(),
  useOptOut: vi.fn(),
  useApproveLate: vi.fn(),
  useReRegister: vi.fn(),
  useSeasons: vi.fn(),
  useCpiDirectory: vi.fn(),
  useCpiFilters: vi.fn(),
  useOfficeRecords: vi.fn(),
  useRecordRevisions: vi.fn(),
  useCorrectRecord: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);
const auth = vi.hoisted(() => ({ can: (_: string): boolean => false }));
vi.mock("../../../auth/AuthProvider", () => ({ useAuth: () => auth }));

function query(over: Record<string, unknown>) {
  return { data: undefined, isPending: false, error: null, ...over };
}

const STUDENT = { season: "2026-27", available: true, registered: 10, placed: 6,
  placement_rate: 60, median_ctc: "9.00", max_ctc: "20.00",
  companies: [{ company: "Acme", placed: 6 }] };
const STAFF = { ...STUDENT, by_company: [{ company__name: "Acme", placed: 6, top: 20 }],
  applications_by_status: { submitted: 3 }, debarred: 0,
  salary_distribution: [{ band: "5-10 LPA", placed: 4 }, { band: "10-15 LPA", placed: 2 }] };

function page() {
  return render(<MantineProvider><ReportsPage /></MantineProvider>);
}

describe("ReportsPage", () => {
  beforeEach(() => {
    auth.can = () => false;
    for (const fn of Object.values(hooks)) fn.mockReturnValue({ ...query({}), mutate: vi.fn() });
    hooks.useSeasons.mockReturnValue(query({ data: [{ season: "2026-27" }] }));
    hooks.useStats.mockReturnValue(query({ data: STUDENT }));
    hooks.useStatsTrends.mockReturnValue(query({ data: [] }));
    hooks.useOutstandingLetters.mockReturnValue(query({ data: { results: [] } }));
  });

  it("shows loading", () => {
    hooks.useStats.mockReturnValue(query({ isPending: true }));
    page();
    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });

  it("renders a real error", () => {
    hooks.useStats.mockReturnValue(query({ error: new Error("boom") }));
    page();
    expect(screen.getByText("Could not load this")).toBeInTheDocument();
  });

  it("says when figures are not published", () => {
    hooks.useStats.mockReturnValue(query({ data: { season: "2026-27", available: false } }));
    page();
    expect(screen.getByText("Statistics are not published yet")).toBeInTheDocument();
  });

  it("gives a student anonymised figures and no office reports", () => {
    page();
    expect(screen.getByText("Placement Statistics")).toBeInTheDocument();
    expect(screen.getByText("60%")).toBeInTheDocument();
    expect(screen.queryByText("Salary package distribution")).not.toBeInTheDocument();
    expect(screen.queryByText("Applications CSV")).not.toBeInTheDocument();
  });

  it("gives the office salary bands, trends and exports", () => {
    auth.can = () => true;
    hooks.useStats.mockReturnValue(query({ data: STAFF }));
    hooks.useStatsTrends.mockReturnValue(query({ data: [{ season: "2026-27", registered: 10,
      placed: 6, placement_rate: 60, companies_participated: 1 }] }));
    page();
    expect(screen.getByText("Salary package distribution")).toBeInTheDocument();
    expect(screen.getByText("5-10 LPA")).toBeInTheDocument();
    expect(screen.getByText("Trends across seasons")).toBeInTheDocument();
    expect(screen.getByText("Applications CSV")).toBeInTheDocument();
  });
});
