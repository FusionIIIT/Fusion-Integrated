import { http } from "../../lib/http";
import type { ApplicationStatus } from "./types";

/**
 * Patent API types and hooks.
 *
 * Endpoints are under /patent/ in the backend, so axios calls use paths like "/patent/mine".
 */

// --- Types ---

export interface PatentApplication {
  id: number;
  title: string;
  abstract: string;
  inventor_names: string[];
  filing_date: string; // ISO date string
  status: ApplicationStatus;
  assigned_director_id: number | null;
  attorney_assigned: boolean;
  budget_total: number | null;
  created_at: string;
  updated_at: string;
}

export interface PatentApplicationCreateData {
  title: string;
  abstract: string;
  inventor_names: string[];
  filing_date: string; // ISO date string
}

// --- Hooks ---

/** Fetches the current user's patent applications. */
export function useMyApplications() {
  return http.get<PatentApplication[]>("/patent/mine");
}

/** Creates a new patent application. */
export async function createPatentApplication(
  data: PatentApplicationCreateData,
): Promise<PatentApplication> {
  const res = await http.post<PatentApplication>(
    "/patent/submit",
    data,
  );
  return res.data;
}

/** Fetches a single patent application by ID. */
export function usePatentApplication(id: number) {
  return http.get<PatentApplication>(`/patent/applications/${id}/`);
}

/** Updates the status or metadata of a patent application (e.g., assign director, withdraw). */
export async function updatePatentApplication(
  id: number,
  data: Partial<PatentApplication>,
): Promise<PatentApplication> {
  const res = await http.patch<PatentApplication>(
    `/patent/applications/${id}/`,
    data,
  );
  return res.data;
}

/** Fetches pending applications for review (Director role). */
export function usePendingApplications() {
  // Assuming a dedicated endpoint or filtering on the list. 
  // For now, we'll assume a specific endpoint exists: /patent/review/pending
  // If not, this would need to be adjusted based on actual backend implementation.
  return http.get<PatentApplication[]>("/patent/review/pending");
}

/** Fetches admin applications (PCC_ADMIN role). */
export function useAdminApplications() {
  return http.get<PatentApplication[]>("/patent/admin/applications");
}

// --- Legal & Filing Hooks (Attorney) ---

/** Records an external patent office filing. */
export async function recordFiling(filingData: any) {
  const res = await http.post(
    "/patent/filings/",
    filingData,
  );
  return res.data;
}

/** Records an office action received from the patent office. */
export async function recordOfficeAction(actionData: any) {
  const res = await http.post(
    "/patent/office-actions/",
    actionData,
  );
  return res.data;
}

/** Prepares a response to an office action. */
export async function prepareResponse(responseData: any) {
  const res = await http.post(
    "/patent/office-actions/prepare/",
    responseData,
  );
  return res.data;
}

/** Approves a prepared response. */
export async function approveResponse(id: number) {
  const res = await http.post(`/patent/office-actions/${id}/approve/`);
  return res.data;
}

/** Submits the final response to the patent office. */
export async function submitResponse(id: number, responseData: any) {
  const res = await http.post(
    `/patent/office-actions/${id}/response/submit/`,
    responseData,
  );
  return res.data;
}

/** Records a grant decision for an application. */
export async function recordGrant(applicationId: number, grantData: any) {
  const res = await http.post(
    `/patent/applications/${applicationId}/grant/`,
    grantData,
  );
  return res.data;
}

/** Schedules a maintenance fee payment. */
export async function scheduleMaintenance(applicationId: number, data: any) {
  const res = await http.post(
    `/patent/maintenance/${applicationId}/`,
    data,
  );
  return res.data;
}

/** Decides on a renewal request. */
export async function decideRenewal(applicationId: number, decisionData: any) {
  const res = await http.post(
    `/patent/maintenance/${applicationId}/decide/`,
    decisionData,
  );
  return res.data;
}

/** Proposes a budget for an application. */
export async function proposeBudget(applicationId: number, budgetData: any) {
  const res = await http.post(
    `/patent/budgets/${applicationId}/`,
    budgetData,
  );
  return res.data;
}

/** Decides on a proposed budget. */
export async function decideBudget(applicationId: number, decisionData: any) {
  const res = await http.post(
    `/patent/budgets/${applicationId}/decide/`,
    decisionData,
  );
  return res.data;
}

/** Records an opinion from the attorney. */
export async function recordOpinion(opinionData: any) {
  const res = await http.post(
    "/patent/opinions/",
    opinionData,
  );
  return res.data;
}

// --- Appeals Hooks ---

/** Files an appeal for an application. */
export async function fileAppeal(applicationId: number, appealData: any) {
  const res = await http.post(
    `/patent/applications/${applicationId}/appeal/`,
    appealData,
  );
  return res.data;
}

/** Reviews and decides on an appeal. */
export async function decideAppeal(appealId: number, decisionData: any) {
  const res = await http.post(
    `/patent/appeals/${appealId}/`,
    decisionData,
  );
  return res.data;
}

// --- Admin Hooks ---

/** Expire overdue resubmissions (system trigger). */
export async function expireOverdueResubmissions() {
  const res = await http.post("/patent/admin/expire-resubmissions/");
  return res.data;
}
