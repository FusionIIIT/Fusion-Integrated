TITLE: Rewrite the client data layer for the new leave API
FORMAT: whole
EDIT: client/src/modules/leave/api.ts
READ: kit:phase2/DESIGN.md modules/leave/api/serializers.py modules/leave/api/urls.py client/src/lib/http.ts
LIMIT: 1200
POST: none
---
Review findings on client/src/modules/leave/api.ts: it calls endpoints that do not exist (/leave/mine, /leave/apply/, /leave/<id>/decide-unit-head/ ...), its "hooks" are not React hooks (they call http.get during render and return a Promise), it imports ApplicationStatus from the placement module (another module's internals are off limits), and its types do not match the server.

Replace the whole file with TypeScript types plus TanStack Query hooks for the API in the "API" section of DESIGN.md. The axios instance `http` already has baseURL "/api/v1", so paths start with "/leave/". The serializers in modules/leave/api/serializers.py (read-only) define the JSON field names; DRF sends DecimalField values as strings.

Start the file with exactly:

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../lib/http";

Types to export: LeaveCategory ("CL" | "RH" | "SCL" | "EL" | "COL" | "VL"), HalfDay ("none" | "first" | "second"), Stage, Status, SubstituteStatus, Decision ("approve" | "reject" | "recommended" | "not_recommended" | "verify"), LeaveAction, LeaveApplication (every field of LeaveApplicationSerializer; days is a string; actions is LeaveAction[]), LeaveBalance (category, year, entitled, used, available; the last three are strings), ApplyInput (the fields of ApplySerializer; substitute_id is number | null). Also export const CATEGORY_LABELS: Record<LeaveCategory, string> = { CL: "Casual Leave", RH: "Restricted Holiday", SCL: "Special Casual Leave", EL: "Earned Leave", COL: "Commuted Leave", VL: "Vacation Leave" }.

List endpoints may return a plain array or a page object, so add:
function asList<T>(data: T[] | { results: T[] }): T[] { return Array.isArray(data) ? data : data.results; }

Queries (query keys all start with "leave"):
- useMyApplications(): GET /leave/applications/ -> LeaveApplication[]
- useInbox(): GET /leave/inbox/ -> LeaveApplication[]
- useBalances(year: number): GET /leave/balances/ with params { year } -> LeaveBalance[]

Mutations (each receives its variables in mutate(...), and on success calls queryClient.invalidateQueries({ queryKey: ["leave"] })):
- useApply(): POST /leave/applications/ with ApplyInput
- useWithdraw(): { id } -> POST /leave/applications/${id}/withdraw/
- useCancel(): { id } -> POST /leave/applications/${id}/cancel/
- useSubstituteResponse(): { id, accept } -> POST /leave/applications/${id}/substitute-response/ with { accept }
- useReplaceSubstitute(): { id, substitute_id } -> POST /leave/applications/${id}/replace-substitute/ with { substitute_id }
- useDecide(): { id, decision, remark } -> POST /leave/applications/${id}/decide/ with { decision, remark }

Follow this pattern from the placement module:

export function usePostings(filters?: { placement_year?: string }) {
  return useQuery({
    queryKey: ["placement", "postings", filters],
    queryFn: async () => (await http.get<Page<Posting>>("/placement/postings", { params: filters })).data,
  });
}

export function useApplyToPosting() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (vars: { id: number }) => (await http.post(`/placement/postings/${vars.id}/apply`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["placement"] }),
  });
}

Write the whole file. Do not ask for more files.
