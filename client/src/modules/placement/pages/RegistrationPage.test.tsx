/** RegistrationPage: error, no season, open route, registered, and refused. */
import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import RegistrationPage from "./RegistrationPage";

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

function query(over: Record<string, unknown>) {
  return { data: undefined, isPending: false, error: null, ...over };
}
const register = vi.fn();

function page() {
  return render(<MantineProvider><RegistrationPage /></MantineProvider>);
}

describe("RegistrationPage", () => {
  beforeEach(() => {
    register.mockReset();
    for (const fn of Object.values(hooks)) fn.mockReturnValue({ ...query({}), mutate: vi.fn() });
    hooks.useRegister.mockReturnValue({ mutate: register, isPending: false });
    hooks.useSeasons.mockReturnValue(query({ data: [
      { season: "2026-27", label: "2026-27", is_active: true }] }));
    hooks.useMyRegistrations.mockReturnValue(query({ data: { results: [] } }));
    hooks.useMyConductRecord.mockReturnValue(query({ data: { results: [] } }));
    hooks.useRegistrationTerms.mockReturnValue(query({ data: {
      route: "open", reason: "open", message: "You may register.", fee: 0, allowed: true } }));
  });

  it("renders a real error", () => {
    hooks.useMyRegistrations.mockReturnValue(query({ error: new Error("boom") }));
    page();
    expect(screen.getByText("Could not load this")).toBeInTheDocument();
  });

  it("says when no season is open", () => {
    hooks.useSeasons.mockReturnValue(query({ data: [] }));
    page();
    expect(screen.getByText("No placement season is open at the moment.")).toBeInTheDocument();
  });

  it("lets a student register on the open route", () => {
    page();
    expect(screen.getByText("Register for 2026-27")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /^Register/ }));
    expect(register).toHaveBeenCalledWith("2026-27", expect.anything());
  });

  it("shows a registered student where they stand", () => {
    hooks.useMyRegistrations.mockReturnValue(query({ data: { results: [{
      id: 1, policy: 1, season: "2026-27", status: "registered", offer_count: 0,
      registered_late: false, registered_at: "2026-11-01T10:00:00Z", debarred_reason: "" }] } }));
    page();
    expect(screen.getByText("You are registered for 2026-27")).toBeInTheDocument();
  });

  it("explains a refusal", () => {
    hooks.useRegistrationTerms.mockReturnValue(query({ data: {
      route: "refused", reason: "cpi_below_minimum", message: "Your CPI is below 6.",
      fee: 0, allowed: false } }));
    page();
    expect(screen.getByText("Your CPI is below 6.")).toBeInTheDocument();
  });
});
