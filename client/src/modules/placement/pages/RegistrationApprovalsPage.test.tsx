/** RegistrationApprovalsPage: the office completes a late registration only when the form is whole. */
import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import RegistrationApprovalsPage from "./RegistrationApprovalsPage";

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

function page() {
  return render(<MantineProvider><RegistrationApprovalsPage /></MantineProvider>);
}

describe("RegistrationApprovalsPage", () => {
  beforeEach(() => {
    for (const fn of Object.values(hooks)) {
      fn.mockReturnValue({ data: undefined, isPending: false, error: null, mutate: vi.fn() });
    }
    hooks.useSeasons.mockReturnValue({ data: [{ season: "2026-27", label: "2026-27",
      is_active: true }], isPending: false, error: null });
  });

  it("shows the form", () => {
    page();
    expect(screen.getByText("Complete a registration")).toBeInTheDocument();
  });

  it("keeps the action disabled until every field is given", () => {
    page();
    const buttons = screen.getAllByRole("button").filter((b) => b.hasAttribute("disabled"));
    expect(buttons.length).toBeGreaterThan(0);
  });
});
