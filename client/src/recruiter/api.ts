/** The recruiter portal's data layer.
 *
 *  A separate axios instance from `lib/http` on purpose: the two apps carry
 *  different credentials, and a 401 in the portal must land on the portal
 *  login rather than the institute one. Authentication is the httpOnly
 *  `recruiter_session` cookie, invisible to this code.
 */
import axios from "axios";
import {
  useMutation, useQuery, useQueryClient,
} from "@tanstack/react-query";

import type {
  Applicant, Company, InterviewRound, Offer, Page, Posting,
} from "../modules/placement/api/types";

export const recruiterHttp = axios.create({
  baseURL: "/api/v1/placement",
  withCredentials: true,
  timeout: 15000,
});

/** A different session from the institute one, so a different token. */
let csrfToken = "";
export function setRecruiterCsrfToken(value: string) {
  csrfToken = value ?? "";
}

const UNSAFE = new Set(["post", "put", "patch", "delete"]);

recruiterHttp.interceptors.request.use((config) => {
  if (csrfToken && UNSAFE.has((config.method ?? "get").toLowerCase())) {
    config.headers.set("X-CSRF-Token", csrfToken);
  }
  return config;
});

let onUnauthorized: (() => void) | null = null;
export function setRecruiterUnauthorizedHandler(fn: () => void) {
  onUnauthorized = fn;
}

recruiterHttp.interceptors.response.use(
  (r) => r,
  (error) => {
    if (error.response?.status === 401) onUnauthorized?.();
    return Promise.reject(error);
  },
);

export interface RecruiterSession {
  csrf_token: string;
  email: string;
  full_name: string;
  company: { id: number; name: string; approval_status: string };
  modules: string[];
}

const K = "recruiter";
const keys = {
  me: [K, "me"] as const,
  postings: [K, "postings"] as const,
  applicants: (f?: unknown) => [K, "applicants", f] as const,
  rounds: [K, "rounds"] as const,
  offers: [K, "offers"] as const,
};

function invalidate(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: [K] });
}

// -- Session -------------------------------------------------------------------
export function useRecruiterSession() {
  return useQuery({
    queryKey: keys.me,
    queryFn: async () =>
      (await recruiterHttp.get<RecruiterSession>("/recruiters/me")).data,
    retry: false,          // a 401 means "not signed in", not "try harder"
    staleTime: 60_000,
  });
}

export function useRecruiterLogin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { email: string; password: string }) =>
      (await recruiterHttp.post<{ csrf_token: string }>(
        "/recruiters/login", body)).data,
    onSuccess: (data) => {
      // Armed here so the first write need not wait for /me.
      setRecruiterCsrfToken(data.csrf_token);
      invalidate(qc);
    },
  });
}

export function useRecruiterLogout() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => recruiterHttp.post("/recruiters/logout", {}),
    onSettled: () => {
      setRecruiterCsrfToken("");
      qc.clear();
    },
  });
}

export function useAcceptInvite() {
  return useMutation({
    mutationFn: async (body: { token: string; password: string }) =>
      (await recruiterHttp.post("/recruiters/accept", body)).data,
  });
}

// -- Postings — scoped to the recruiter's own company by the server ------------
export function useMyPostings() {
  return useQuery({
    queryKey: keys.postings,
    queryFn: async () =>
      (await recruiterHttp.get<Page<Posting>>("/postings")).data,
    staleTime: 30_000,
  });
}

export function useCreateMyPosting() {
  const qc = useQueryClient();
  return useMutation({
    // No company_id: the server takes it from the credential.
    mutationFn: async (body: Record<string, unknown>) =>
      (await recruiterHttp.post<Posting>("/postings", body)).data,
    onSuccess: () => invalidate(qc),
  });
}

export function usePublishMyPosting() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await recruiterHttp.post<Posting>(`/postings/${id}/publish`, {})).data,
    onSuccess: () => invalidate(qc),
  });
}

// -- Applicants ----------------------------------------------------------------
export function useMyApplicants(filters?: { posting?: number; status?: string }) {
  return useQuery({
    queryKey: keys.applicants(filters),
    queryFn: async () =>
      (await recruiterHttp.get<Page<Applicant>>("/applications",
        { params: filters })).data,
    staleTime: 15_000,
  });
}

export function useApplicantTransition() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, to_status, reason }:
      { id: number; to_status: string; reason?: string }) =>
      (await recruiterHttp.post(`/applications/${id}/transition`,
        { to_status, reason: reason ?? "" })).data,
    onSuccess: () => invalidate(qc),
  });
}

export function useIssueMyOffer() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      application_id: number; ctc_lpa?: string; respond_by?: string;
    }) => (await recruiterHttp.post<Offer>("/offers/issue", body)).data,
    onSuccess: () => invalidate(qc),
  });
}

export function useMyOffers() {
  return useQuery({
    queryKey: keys.offers,
    queryFn: async () => (await recruiterHttp.get<Page<Offer>>("/offers")).data,
    staleTime: 30_000,
  });
}

// -- Interviews ----------------------------------------------------------------
export function useMyRounds() {
  return useQuery({
    queryKey: keys.rounds,
    queryFn: async () =>
      (await recruiterHttp.get<Page<InterviewRound>>("/interviews/rounds")).data,
    staleTime: 30_000,
  });
}

export function useScheduleMyRound() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) =>
      (await recruiterHttp.post<InterviewRound>("/interviews/rounds", body)).data,
    onSuccess: () => invalidate(qc),
  });
}

export function useAddMyCandidates() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ roundId, applicationIds }:
      { roundId: number; applicationIds: number[] }) =>
      (await recruiterHttp.post(`/interviews/rounds/${roundId}/candidates`,
        { application_ids: applicationIds })).data,
    onSuccess: () => invalidate(qc),
  });
}

export type { Applicant, Company, InterviewRound, Offer, Posting };
