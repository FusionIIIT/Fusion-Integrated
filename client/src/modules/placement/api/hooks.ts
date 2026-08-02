/** Data access for the placement module.
 *
 *  Every mutation invalidates the keys it can affect; no manual cache surgery.
 *  Getting that subtly wrong shows up as an enabled "Apply" button on a
 *  posting the student already applied to.
 */
import {
  useMutation, useQuery, useQueryClient, type UseMutationOptions,
} from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  Announcement, Applicant, Application, Company, EligibilityVerdict,
  InterviewRound, Offer, Page, Posting, ProfileDocument, StaffStats,
  StudentProfile, StudentStats,
} from "./types";

const KEY = "placement";

export const keys = {
  postings: (f?: unknown) => [KEY, "postings", f] as const,
  posting: (id: number) => [KEY, "posting", id] as const,
  eligibility: (id: number) => [KEY, "eligibility", id] as const,
  applications: (f?: unknown) => [KEY, "applications", f] as const,
  offers: () => [KEY, "offers"] as const,
  profile: () => [KEY, "profile"] as const,
  resume: () => [KEY, "resume"] as const,
  companies: () => [KEY, "companies"] as const,
  rounds: (postingId?: number) => [KEY, "rounds", postingId] as const,
  announcements: () => [KEY, "announcements"] as const,
  stats: (season?: string) => [KEY, "stats", season] as const,
};

/** Coarse on purpose — these pages are small, and correctness beats shaving
 *  a refetch. */
function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: [KEY] });
}

// -- Postings ------------------------------------------------------------------
export function usePostings(filters?: { placement_year?: string; kind?: string }) {
  return useQuery({
    queryKey: keys.postings(filters),
    queryFn: async () =>
      (await http.get<Page<Posting>>("/placement/postings", { params: filters }))
        .data,
    staleTime: 30_000,
  });
}

export function usePosting(id: number | undefined) {
  return useQuery({
    queryKey: keys.posting(id!),
    queryFn: async () =>
      (await http.get<Posting>(`/placement/postings/${id}`)).data,
    enabled: id != null,
  });
}

/** The "why can't I apply?" call, fetched when a posting is opened.
 *
 *  Deliberately not folded into the list query — it reaches the IAM for a
 *  declared CPI, so per-row would be fifty round trips nobody asked for. */
export function useEligibility(postingId: number | undefined) {
  return useQuery({
    queryKey: keys.eligibility(postingId!),
    queryFn: async () =>
      (await http.get<EligibilityVerdict>(
        `/placement/postings/${postingId}/eligibility`)).data,
    enabled: postingId != null,
    retry: false,     // a 503 from the IAM should surface, not be retried away
    staleTime: 60_000,
  });
}

export function useCreatePosting() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) =>
      (await http.post<Posting>("/placement/postings", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function usePublishPosting() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await http.post<Posting>(`/placement/postings/${id}/publish`, {})).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Applications --------------------------------------------------------------
export function useApplications(filters?: { status?: string; posting?: number }) {
  return useQuery({
    queryKey: keys.applications(filters),
    queryFn: async () =>
      (await http.get<Page<Application & Applicant>>(
        "/placement/applications", { params: filters })).data,
    staleTime: 15_000,
  });
}

export function useApply() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { posting_id: number; cover_note?: string }) =>
      (await http.post<Application>("/placement/applications/apply", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useTransition(
  options?: Pick<UseMutationOptions<Application, unknown,
    { id: number; to_status: string; reason?: string }>, "onSuccess" | "onError">,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, to_status, reason }:
      { id: number; to_status: string; reason?: string }) =>
      (await http.post<Application>(
        `/placement/applications/${id}/transition`,
        { to_status, reason: reason ?? "" })).data,
    onSuccess: (...args) => { invalidateAll(qc); options?.onSuccess?.(...args); },
    onError: options?.onError,
  });
}

// -- Offers --------------------------------------------------------------------
export function useOffers() {
  return useQuery({
    queryKey: keys.offers(),
    queryFn: async () => (await http.get<Page<Offer>>("/placement/offers")).data,
    // Short, because a deadline is ticking and an expired offer must not keep
    // rendering an enabled Accept button.
    staleTime: 10_000,
  });
}

export function useIssueOffer() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      application_id: number; ctc_lpa?: string; respond_by?: string;
    }) => (await http.post<Offer>("/placement/offers/issue", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useRespondToOffer() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, accept }: { id: number; accept: boolean }) =>
      (await http.post<Offer>(`/placement/offers/${id}/respond`, { accept })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Profile -------------------------------------------------------------------
export function useMyProfile() {
  return useQuery({
    queryKey: keys.profile(),
    queryFn: async () =>
      (await http.get<StudentProfile>("/placement/profile")).data,
  });
}

export function useSaveProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) =>
      (await http.put<StudentProfile>("/placement/profile", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useMyResume() {
  return useQuery({
    queryKey: keys.resume(),
    queryFn: async () =>
      (await http.get<Record<string, unknown>>("/placement/profile/resume")).data,
  });
}

// -- Companies -----------------------------------------------------------------
export function useCompanies() {
  return useQuery({
    queryKey: keys.companies(),
    queryFn: async () =>
      (await http.get<Page<Company>>("/placement/companies")).data,
    staleTime: 30_000,
  });
}

export function useRegisterCompany() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) =>
      (await http.post<Company>("/placement/companies", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useCompanyDecision() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, action, note }: {
      id: number; action: "approve" | "reject" | "blacklist"; note?: string;
    }) => (await http.post<Company>(
      `/placement/companies/${id}/${action}`, { note: note ?? "" })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useInviteRecruiter() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      company_id: number; email: string; full_name?: string;
    }) => (await http.post<{
      account_id: number; email: string; invite_token: string;
      expires_at: string;
    }>("/placement/recruiters/invite", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Interviews ----------------------------------------------------------------
export function useRounds(postingId?: number) {
  return useQuery({
    queryKey: keys.rounds(postingId),
    queryFn: async () =>
      (await http.get<Page<InterviewRound>>("/placement/interviews/rounds",
        { params: postingId ? { posting: postingId } : undefined })).data,
    staleTime: 30_000,
  });
}

export function useScheduleRound() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) =>
      (await http.post<InterviewRound>("/placement/interviews/rounds", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useAddCandidates() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ roundId, applicationIds }: {
      roundId: number; applicationIds: number[];
    }) => (await http.post<{ scheduled: number }>(
      `/placement/interviews/rounds/${roundId}/candidates`,
      { application_ids: applicationIds })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Announcements -------------------------------------------------------------
export function useAnnouncements() {
  return useQuery({
    queryKey: keys.announcements(),
    queryFn: async () =>
      (await http.get<Page<Announcement>>("/placement/announcements")).data,
    staleTime: 30_000,
  });
}

export function usePublishAnnouncement() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) =>
      (await http.post<Announcement>("/placement/announcements", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useWithdrawAnnouncement() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, reason }: { id: number; reason: string }) =>
      (await http.post<Announcement>(
        `/placement/announcements/${id}/withdraw`, { reason })).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Statistics ----------------------------------------------------------------
export function useStats(season?: string) {
  return useQuery({
    queryKey: keys.stats(season),
    queryFn: async () =>
      (await http.get<StudentStats & StaffStats>("/placement/stats",
        { params: season ? { season } : undefined })).data,
    staleTime: 60_000,
  });
}

// -- Documents -----------------------------------------------------------------
export function useMyDocuments() {
  return useQuery({
    queryKey: [KEY, "documents"],
    queryFn: async () =>
      (await http.get<{ results: ProfileDocument[] }>("/placement/documents")).data,
  });
}

/** Attach a Drive link. The server rebuilds the URL from the file id. */
export function useAttachDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { url: string; kind: string; title?: string }) =>
      (await http.post<ProfileDocument>("/placement/documents", body)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useDeleteDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => http.delete(`/placement/documents/${id}`),
    onSuccess: () => invalidateAll(qc),
  });
}

/** The authorising view. The raw Drive URL is absent from list payloads. */
export function documentDownloadUrl(id: number): string {
  return `/api/v1/placement/documents/${id}/download`;
}

// -- CPI directory (staff only) ------------------------------------------------
export interface CpiRow {
  user_id: number;
  roll_no: string;
  name: string;
  discipline: string;
  programme: string;
  batch_year: number | null;
  /** null = no DECLARED result. Never render this as 0.00. */
  cpi: string | null;
  earned_credits: string | null;
  active_backlogs: number | null;
  semester: number | null;
  semester_type: string | null;
  synced_at: string | null;
}

export interface CpiPage {
  count: number;
  limit: number;
  offset: number;
  results: CpiRow[];
}

export function useCpiDirectory(filters: {
  q?: string; discipline?: string; batch_year?: string; programme?: string;
  only_declared?: boolean; limit?: number; offset?: number;
}) {
  return useQuery({
    queryKey: [KEY, "cpi", filters],
    queryFn: async () =>
      (await http.get<CpiPage>("/placement/students/cpi", { params: filters })).data,
    // Declared results change only on an exam-office announcement.
    staleTime: 120_000,
    placeholderData: (prev) => prev,      // no flicker while typing a search
  });
}

export function useCpiFilters() {
  return useQuery({
    queryKey: [KEY, "cpi-filters"],
    queryFn: async () =>
      (await http.get<{
        disciplines: string[]; batch_years: number[]; programmes: string[];
      }>("/placement/students/cpi/filters")).data,
    staleTime: 600_000,
  });
}
