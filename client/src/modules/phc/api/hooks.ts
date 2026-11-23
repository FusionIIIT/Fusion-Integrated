// One TanStack Query hook per PHC endpoint; every mutation invalidates the whole module.
import {
  useInfiniteQuery, useMutation, useQuery, useQueryClient,
} from "@tanstack/react-query";

import { filenameFromDisposition, saveBlob } from "../../../lib/download";
import { http, readBlobError } from "../../../lib/http";
import type {
  Advisory, AmbulanceInput, AmbulanceLog, AttendanceStatus, Claim, ClaimEvent, ClaimInput,
  EligiblePrescription, InventoryItem, InventoryItemInput, LowStockAlert, Notification, Page,
  Patient, Report, ReportCategory, Requisition, RequisitionEvent, RequisitionInput, Schedule,
  ScheduleInput, StockAdjustment, Visit, VisitInput,
} from "./types";

const KEY = "phc";

function useInvalidate() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: [KEY] });
}

function useList<T>(name: string, path: string, params?: object) {
  return useQuery({
    queryKey: [KEY, name, params],
    queryFn: async () => (await http.get<T>(path, { params })).data,
  });
}

function cursorOf(next: string | null): string | undefined {
  if (!next) return undefined;
  return new URL(next, "http://x").searchParams.get("cursor") ?? undefined;
}

// A cursor-paginated list: `data.results` holds every page loaded so far.
function usePaged<T>(name: string, path: string) {
  const query = useInfiniteQuery({
    queryKey: [KEY, name],
    queryFn: async ({ pageParam }) => (await http.get<Page<T>>(path, {
      params: pageParam ? { cursor: pageParam } : undefined,
    })).data,
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) => cursorOf(last.next),
  });
  const results = query.data?.pages.flatMap((p) => p.results);
  return {
    data: results ? { results } : undefined,
    isPending: query.isPending,
    error: query.error,
    hasNextPage: query.hasNextPage,
    fetchNextPage: query.fetchNextPage,
    isFetchingNextPage: query.isFetchingNextPage,
  };
}

export type PagedList = Pick<ReturnType<typeof usePaged>,
  "hasNextPage" | "fetchNextPage" | "isFetchingNextPage">;

function useWrite<TIn, TOut>(send: (input: TIn) => Promise<TOut>) {
  const invalidate = useInvalidate();
  return useMutation({ mutationFn: send, onSuccess: invalidate });
}

// -- Schedules ---------------------------------------------------------------------
export const useSchedules = () => useList<Schedule[]>("schedules", "/phc/schedules");

export const useCreateSchedule = () => useWrite(async (input: ScheduleInput) =>
  (await http.post<Schedule>("/phc/schedules", input)).data);

export const useUpdateSchedule = () => useWrite(
  async ({ id, ...input }: ScheduleInput & { id: number }) =>
    (await http.put<Schedule>(`/phc/schedules/${id}`, input)).data);

export const usePublishSchedule = () => useWrite(async (id: number) =>
  (await http.post<Schedule>(`/phc/schedules/${id}/publish`)).data);

export const useMarkAttendance = () => useWrite(
  async ({ id, status }: { id: number; status: AttendanceStatus }) =>
    (await http.post(`/phc/schedules/${id}/attendance`, { status })).data);

// -- Records -----------------------------------------------------------------------
export function useVisit(id: number | null) {
  return useQuery({
    queryKey: [KEY, "visit", id],
    queryFn: async () => (await http.get<Visit>(`/phc/records/${id}`)).data,
    enabled: id !== null,
  });
}

export const useVisits = () => usePaged<Visit>("visits", "/phc/records");

export function usePatientSearch(q: string) {
  return useQuery({
    queryKey: [KEY, "patients", q],
    queryFn: async () => (await http.get<Patient[]>("/phc/patients", { params: { q } })).data,
    enabled: q.trim().length >= 2,
  });
}

export const useRecordVisit = () => useWrite(async (input: VisitInput) =>
  (await http.post<Visit>("/phc/records", input)).data);

export function useDownloadRecords() {
  return useMutation({
    mutationFn: async (ids: number[]) => {
      try {
        const res = await http.get("/phc/records/pdf", {
          params: { ids: ids.join(",") }, responseType: "blob",
        });
        saveBlob(res.data, filenameFromDisposition(
          res.headers["content-disposition"], "phc-medical-records.pdf"));
      } catch (e) {
        throw await readBlobError(e);
      }
    },
  });
}

// -- Claims ------------------------------------------------------------------------
export function useClaim(id: number | null) {
  return useQuery({
    queryKey: [KEY, "claim", id],
    queryFn: async () => (await http.get<Claim>(`/phc/claims/${id}`)).data,
    enabled: id !== null,
  });
}

// Every inventory item, following each page, for pickers that must offer any item.
export function useAllInventory(enabled: boolean) {
  return useQuery({
    queryKey: [KEY, "inventory-all"],
    queryFn: async () => {
      const items: InventoryItem[] = [];
      let cursor: string | undefined;
      do {
        const page = (await http.get<Page<InventoryItem>>("/phc/inventory", {
          params: cursor ? { cursor } : undefined,
        })).data;
        items.push(...page.results);
        cursor = cursorOf(page.next);
      } while (cursor);
      return items;
    },
    enabled,
  });
}

export const useClaims = () => usePaged<Claim>("claims", "/phc/claims");

export function useEligiblePrescriptions(enabled: boolean) {
  return useQuery({
    queryKey: [KEY, "eligible-prescriptions"],
    queryFn: async () =>
      (await http.get<EligiblePrescription[]>("/phc/claims/prescriptions")).data,
    enabled,
  });
}

export const useSubmitClaim = () => useWrite(async (input: ClaimInput) =>
  (await http.post<Claim>("/phc/claims", input)).data);

export const useClaimTransition = () => useWrite(
  async ({ id, event, note }: { id: number; event: ClaimEvent; note: string }) =>
    (await http.post<Claim>(`/phc/claims/${id}/transition`, { event, note })).data);

// -- Inventory ---------------------------------------------------------------------
export const useInventory = () => usePaged<InventoryItem>("inventory", "/phc/inventory");

export const useLowStockAlerts = () =>
  usePaged<LowStockAlert>("alerts", "/phc/inventory/alerts");

export const useCreateItem = () => useWrite(async (input: InventoryItemInput) =>
  (await http.post<InventoryItem>("/phc/inventory", input)).data);

export const useAdjustStock = () => useWrite(
  async ({ id, delta, reason }: { id: number; delta: string; reason: string }) =>
    (await http.post<StockAdjustment>(`/phc/inventory/${id}/adjust`, { delta, reason })).data);

// -- Requisitions ------------------------------------------------------------------
export const useRequisitions = () =>
  usePaged<Requisition>("requisitions", "/phc/requisitions");

export const useSubmitRequisition = () => useWrite(async (input: RequisitionInput) =>
  (await http.post<Requisition>("/phc/requisitions", input)).data);

export const useRequisitionTransition = () => useWrite(
  async ({ id, event, note }: { id: number; event: RequisitionEvent; note: string }) =>
    (await http.post<Requisition>(`/phc/requisitions/${id}/transition`, { event, note })).data);

// -- Ambulance, advisories, reports, notifications --------------------------------
export const useAmbulanceLogs = () => usePaged<AmbulanceLog>("ambulance", "/phc/ambulance");

export const useLogAmbulance = () => useWrite(async (input: AmbulanceInput) =>
  (await http.post<AmbulanceLog>("/phc/ambulance", input)).data);

export const useAdvisories = () => usePaged<Advisory>("advisories", "/phc/advisories");

export const usePublishAdvisory = () => useWrite(
  async (input: { title: string; body: string }) =>
    (await http.post<Advisory>("/phc/advisories", input)).data);

export function useReport(params: { category: ReportCategory; start: string; end: string } | null) {
  return useQuery({
    queryKey: [KEY, "report", params],
    queryFn: async () => (await http.get<Report>("/phc/reports", { params })).data,
    enabled: params !== null,
  });
}

export const useNotifications = () =>
  usePaged<Notification>("notifications", "/phc/notifications");
