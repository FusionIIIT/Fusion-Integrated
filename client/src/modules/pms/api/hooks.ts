import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  AttorneyPanelEntry, LicensingRequest, OfficeAction, PatentApplication,
  PmsAuditEntry, PmsConfiguration, PmsReport, WorkflowOversight,
} from "./types";

const ROOT = "/pms";
const KEY = "pms";

export const pmsKeys = {
  all: [KEY] as const,
  applications: () => [KEY, "applications"] as const,
  application: (id: number | undefined) => [KEY, "application", id] as const,
  officeActions: (id: number | undefined) => [KEY, "office-actions", id] as const,
  licensing: (id: number | undefined) => [KEY, "licensing", id] as const,
  reports: () => [KEY, "reports"] as const,
  workflow: () => [KEY, "workflow"] as const,
  audit: (filters?: unknown) => [KEY, "audit", filters] as const,
  panel: () => [KEY, "panel"] as const,
  configuration: () => [KEY, "configuration"] as const,
};

export function usePmsApplications() {
  return useQuery({
    queryKey: pmsKeys.applications(),
    queryFn: async () =>
      (await http.get<PatentApplication[]>(`${ROOT}/applications/`)).data,
    staleTime: 15_000,
  });
}

export function usePmsApplication(id: number | undefined) {
  return useQuery({
    queryKey: pmsKeys.application(id),
    queryFn: async () =>
      (await http.get<PatentApplication>(`${ROOT}/applications/${id}/`)).data,
    enabled: id != null,
  });
}

export function useOfficeActions(id: number | undefined) {
  return useQuery({
    queryKey: pmsKeys.officeActions(id),
    queryFn: async () =>
      (await http.get<OfficeAction[]>(`${ROOT}/applications/${id}/office-actions/`))
        .data,
    enabled: id != null,
  });
}

export function useLicensingRequests(id: number | undefined) {
  return useQuery({
    queryKey: pmsKeys.licensing(id),
    queryFn: async () =>
      (await http.get<LicensingRequest[]>(`${ROOT}/applications/${id}/licensing/`))
        .data,
    enabled: id != null,
  });
}

export function usePmsReports() {
  return useQuery({
    queryKey: pmsKeys.reports(),
    queryFn: async () => (await http.get<PmsReport>(`${ROOT}/reports/`)).data,
  });
}

export function useWorkflowOversight() {
  return useQuery({
    queryKey: pmsKeys.workflow(),
    queryFn: async () =>
      (await http.get<WorkflowOversight[]>(`${ROOT}/workflow-oversight/`)).data,
  });
}

export function usePmsAudit(applicationId?: number) {
  return useQuery({
    queryKey: pmsKeys.audit(applicationId),
    queryFn: async () =>
      (await http.get<PmsAuditEntry[]>(`${ROOT}/audit-trail/`, {
        params: applicationId ? { application_id: applicationId } : undefined,
      })).data,
  });
}

export function useAttorneyPanel() {
  return useQuery({
    queryKey: pmsKeys.panel(),
    queryFn: async () =>
      (await http.get<AttorneyPanelEntry[]>(`${ROOT}/attorney-panel/`)).data,
  });
}

export function usePmsConfiguration() {
  return useQuery({
    queryKey: pmsKeys.configuration(),
    queryFn: async () =>
      (await http.get<PmsConfiguration[]>(`${ROOT}/configuration/`)).data,
  });
}

export type PmsMethod = "post" | "put" | "patch" | "delete";

/** All writes go through the shared cookie/CSRF client and invalidate the PMS
 *  query family only after the server confirms success. */
export function usePmsAction<TBody extends Record<string, unknown> = Record<string, unknown>, TResult = unknown>(
  method: PmsMethod,
  path: (body: TBody) => string,
) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (body: TBody) => {
      const url = `${ROOT}${path(body)}`;
      if (method === "post") return (await http.post<TResult>(url, body)).data;
      if (method === "put") return (await http.put<TResult>(url, body)).data;
      if (method === "patch") return (await http.patch<TResult>(url, body)).data;
      return (await http.delete<TResult>(url)).data;
    },
    onSuccess: () => client.invalidateQueries({ queryKey: pmsKeys.all }),
  });
}

export const pmsApiRoot = ROOT;
