/** Data access for the VMS module.
 *
 *  One coarse query-key prefix: every mutation invalidates all of `vms`. The screens are
 *  small and correctness beats shaving a refetch — a stale roster after a check-out is
 *  worse than one extra request.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { filenameFromDisposition, saveBlob } from "../../../lib/download";
import { http, readBlobError } from "../../../lib/http";
import type {
  Arrival, BlacklistVersion, BulkDecisionResult, CursorPage, Dashboard, Decision,
  Denial, ExportFormat, GateOutcome, HostRequest, MusterEntry, Muster, OnSiteVisitor,
  Policy, ReportDef, ReportResult, ResultList, RoleAssignment, RollCallStatus,
  VmsEvent, VmsNotification, Zone,
} from "./types";

const KEY = "vms";

export const keys = {
  inbox: () => [KEY, "inbox"] as const,
  arrivals: () => [KEY, "arrivals"] as const,
  hostRequests: (status?: string) => [KEY, "host-requests", status] as const,
  denials: (status?: string) => [KEY, "denials", status] as const,
  onSite: () => [KEY, "on-site"] as const,
  dashboard: () => [KEY, "dashboard"] as const,
  muster: () => [KEY, "muster"] as const,
  musterRoster: (id: number | undefined) => [KEY, "muster-roster", id] as const,
  events: () => [KEY, "events"] as const,
  reportCatalogue: () => [KEY, "report-catalogue"] as const,
  report: (key: string, params: unknown) => [KEY, "report", key, params] as const,
  policies: () => [KEY, "policies"] as const,
  blacklistVersions: () => [KEY, "blacklist-versions"] as const,
  roles: () => [KEY, "roles"] as const,
  zones: () => [KEY, "zones"] as const,
};

function useInvalidateAll() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: [KEY] });
}

// -- Notifications -----------------------------------------------------------------
export function useInbox() {
  return useQuery({
    queryKey: keys.inbox(),
    queryFn: async () =>
      (await http.get<ResultList<VmsNotification>>("/vms/notify/inbox")).data,
  });
}

export function useArrivals(enabled = true) {
  return useQuery({
    queryKey: keys.arrivals(),
    enabled,
    queryFn: async () =>
      (await http.get<ResultList<Arrival>>("/vms/notify/arrivals")).data,
  });
}

export function useMarkRead() {
  const invalidate = useInvalidateAll();
  return useMutation({
    mutationFn: async (id: number) =>
      (await http.post<VmsNotification>(`/vms/notify/${id}/read`)).data,
    onSuccess: invalidate,
  });
}

export function useMarkAllRead() {
  const invalidate = useInvalidateAll();
  return useMutation({
    mutationFn: async () =>
      (await http.post<{ marked: number }>("/vms/notify/read-all")).data,
    onSuccess: invalidate,
  });
}

// -- Host approvals ----------------------------------------------------------------
export function useHostRequests(status = "pending") {
  return useQuery({
    queryKey: keys.hostRequests(status),
    queryFn: async () =>
      (await http.get<CursorPage<HostRequest>>("/vms/host/requests", {
        params: { status },
      })).data,
  });
}

export function useDecide() {
  const invalidate = useInvalidateAll();
  return useMutation({
    mutationFn: async (v: { id: number; decision: Decision; note?: string }) =>
      (await http.post(`/vms/host/requests/${v.id}/decision`, {
        decision: v.decision, note: v.note ?? "",
      })).data,
    onSuccess: invalidate,
  });
}

export function useBulkDecide() {
  const invalidate = useInvalidateAll();
  return useMutation({
    mutationFn: async (v: { ids: number[]; decision: Decision; note?: string }) =>
      (await http.post<{ results: BulkDecisionResult[] }>(
        "/vms/host/requests/bulk-decision",
        { ids: v.ids, decision: v.decision, note: v.note ?? "" },
      )).data,
    onSuccess: invalidate,
  });
}

// -- Gate ----------------------------------------------------------------------------
/** A denial comes back as HTTP 403 with the failure list; for the gate screen that is a
 *  normal outcome to show, not an error to throw away, so it is returned as data. */
async function gateCall(path: string, body: unknown): Promise<GateOutcome> {
  try {
    return (await http.post<GateOutcome>(path, body)).data;
  } catch (e) {
    const res = (e as { response?: { status?: number; data?: GateOutcome } }).response;
    if (res?.status === 403 && res.data?.detail) return { ...res.data, code: res.data.code ?? "denied" };
    throw e;
  }
}

export function useValidate() {
  const invalidate = useInvalidateAll();
  return useMutation({
    mutationFn: (v: { credential: string; gate_id: number }) => {
      const key = /^\d{6}$/.test(v.credential.trim()) ? "otp" : "qr_token";
      return gateCall("/vms/gate/validate", { [key]: v.credential.trim(), gate_id: v.gate_id });
    },
    onSuccess: invalidate,
  });
}

export function useCheckOut() {
  const invalidate = useInvalidateAll();
  return useMutation({
    mutationFn: async (v: { credential: string; gate_id?: number | null }) =>
      (await http.post<{ detail: string }>("/vms/visit/check-out", {
        credential: v.credential.trim(), gate_id: v.gate_id ?? null,
      })).data,
    onSuccess: invalidate,
  });
}

export function useDenials(status = "open") {
  return useQuery({
    queryKey: keys.denials(status),
    queryFn: async () =>
      (await http.get<ResultList<Denial>>("/vms/gate/denials", { params: { status } })).data,
  });
}

export function useOverride() {
  const invalidate = useInvalidateAll();
  return useMutation({
    mutationFn: async (v: { denial_log_id: number; justification: string }) =>
      (await http.post("/vms/gate/override", v)).data,
    onSuccess: invalidate,
  });
}

// -- Roster and monitor ----------------------------------------------------------------
export function useOnSite() {
  return useQuery({
    queryKey: keys.onSite(),
    queryFn: async () =>
      (await http.get<ResultList<OnSiteVisitor>>("/vms/monitor/on-site")).data,
    refetchInterval: 30_000,
  });
}

export function useDashboard() {
  return useQuery({
    queryKey: keys.dashboard(),
    queryFn: async () => (await http.get<Dashboard>("/vms/monitor/dashboard")).data,
    refetchInterval: 30_000,
  });
}

export function useTerminatePass() {
  const invalidate = useInvalidateAll();
  return useMutation({
    mutationFn: async (v: { pass_id: number; reason: string }) =>
      (await http.post(`/vms/visit/passes/${v.pass_id}/terminate`, { reason: v.reason })).data,
    onSuccess: invalidate,
  });
}

// -- Muster ----------------------------------------------------------------------------
export function useCurrentMuster() {
  return useQuery({
    queryKey: keys.muster(),
    queryFn: async () =>
      (await http.get<{ muster: Muster | null }>("/vms/muster/current")).data.muster,
    refetchInterval: 15_000,
  });
}

export function useMusterRoster(id: number | undefined) {
  return useQuery({
    queryKey: keys.musterRoster(id),
    enabled: id !== undefined,
    queryFn: async () =>
      (await http.get<ResultList<MusterEntry>>(`/vms/muster/${id}/roster`)).data,
    refetchInterval: 15_000,
  });
}

export function useTriggerMuster() {
  const invalidate = useInvalidateAll();
  return useMutation({
    mutationFn: async (reason: string) =>
      (await http.post<Muster>("/vms/muster", { reason })).data,
    onSuccess: invalidate,
  });
}

export function useRollCall(musterId: number) {
  const invalidate = useInvalidateAll();
  return useMutation({
    mutationFn: async (v: { pass_id: number; status: RollCallStatus }) =>
      (await http.post(`/vms/muster/${musterId}/roll-call`, v)).data,
    onSuccess: invalidate,
  });
}

export function useCloseMuster(musterId: number) {
  const invalidate = useInvalidateAll();
  return useMutation({
    mutationFn: async (v: { note?: string; force?: boolean }) =>
      (await http.post(`/vms/muster/${musterId}/close`, v)).data,
    onSuccess: invalidate,
  });
}

// -- Events ----------------------------------------------------------------------------
export function useEvents() {
  return useQuery({
    queryKey: keys.events(),
    queryFn: async () => (await http.get<VmsEvent[]>("/vms/events")).data,
  });
}

export function useApproveEvent() {
  const invalidate = useInvalidateAll();
  return useMutation({
    mutationFn: async (id: number) => (await http.post(`/vms/events/${id}/approve`, {})).data,
    onSuccess: invalidate,
  });
}

export function useCancelEvent() {
  const invalidate = useInvalidateAll();
  return useMutation({
    mutationFn: async (v: { id: number; reason: string }) =>
      (await http.post(`/vms/events/${v.id}/cancel`, { reason: v.reason })).data,
    onSuccess: invalidate,
  });
}

// -- Reports ---------------------------------------------------------------------------
export function useReportCatalogue() {
  return useQuery({
    queryKey: keys.reportCatalogue(),
    queryFn: async () => (await http.get<ReportDef[]>("/vms/reports")).data,
    staleTime: 5 * 60_000,
  });
}

export function useRunReport(key: string | null, params: Record<string, string>) {
  return useQuery({
    queryKey: keys.report(key ?? "", params),
    enabled: key !== null,
    queryFn: async () =>
      (await http.get<ReportResult>(`/vms/reports/${key}`, { params })).data,
  });
}

/** PDF and CSV are fetched, not navigated to, so a refusal shows as an error here instead
 *  of replacing the app with the server's error page. */
export function useReportExport() {
  return useMutation({
    mutationFn: async (v: { key: string; params: Record<string, string>; fmt: ExportFormat }) => {
      try {
        const res = await http.get(`/vms/reports/${v.key}/export`, {
          params: { ...v.params, fmt: v.fmt }, responseType: "blob",
        });
        saveBlob(
          res.data as Blob,
          filenameFromDisposition(res.headers["content-disposition"], `${v.key}.${v.fmt}`),
        );
      } catch (e) {
        throw await readBlobError(e);
      }
    },
  });
}

// -- Administration ----------------------------------------------------------------------
export function usePolicies() {
  return useQuery({
    queryKey: keys.policies(),
    queryFn: async () => (await http.get<Policy[]>("/vms/policies")).data,
  });
}

export function usePublishPolicy() {
  const invalidate = useInvalidateAll();
  return useMutation({
    mutationFn: async (id: number) =>
      (await http.post<Policy>(`/vms/policies/${id}/publish`)).data,
    onSuccess: invalidate,
  });
}

export function useBlacklistVersions() {
  return useQuery({
    queryKey: keys.blacklistVersions(),
    queryFn: async () =>
      (await http.get<BlacklistVersion[]>("/vms/blacklist/versions")).data,
  });
}

export function usePublishBlacklist() {
  const invalidate = useInvalidateAll();
  return useMutation({
    mutationFn: async (id: number) =>
      (await http.post<BlacklistVersion>(`/vms/blacklist/versions/${id}/publish`)).data,
    onSuccess: invalidate,
  });
}

export function useRoles() {
  return useQuery({
    queryKey: keys.roles(),
    queryFn: async () => (await http.get<RoleAssignment[]>("/vms/roles")).data,
  });
}

export function useRevokeRole() {
  const invalidate = useInvalidateAll();
  return useMutation({
    mutationFn: async (id: number) =>
      (await http.post<RoleAssignment>(`/vms/roles/${id}/revoke`)).data,
    onSuccess: invalidate,
  });
}

export function useZones() {
  return useQuery({
    queryKey: keys.zones(),
    queryFn: async () => (await http.get<Zone[]>("/vms/zones")).data,
  });
}
