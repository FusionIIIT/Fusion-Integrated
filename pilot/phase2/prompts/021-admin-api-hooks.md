Found in the end-to-end browser test: the Leave Administrator has no screen at all. Reporting lines (who a person's Unit Head, Establishment officer and Sanctioning Authority are, EL-UC-014) can only be set by calling the API by hand, so a new employee cannot be routed. The next tasks add an admin page; this one adds its data hooks. Fix only this, with one SEARCH/REPLACE edit that appends to the END of client/src/modules/leave/api.ts (after the last function) exactly these declarations:

/** Who decides a person's leave (ReportingLineSerializer). */
export interface ReportingLine {
  user_id: number;
  unit_head_id: number;
  establishment_id: number | null;
  sanctioning_authority_id: number | null;
}

/** Load one person's reporting line; a 404 means none is configured yet. */
export function useReportingLine(userId: number | null) {
  return useQuery({
    queryKey: ["leave", "reporting-line", userId],
    queryFn: async () => (await http.get<ReportingLine>(`/leave/reporting-lines/${userId}/`)).data,
    enabled: userId !== null,
    retry: false,
  });
}

/** Create or replace a person's reporting line (Leave Administrator only). */
export function useSetReportingLine() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (vars: ReportingLine) =>
      (await http.put<ReportingLine>(`/leave/reporting-lines/${vars.user_id}/`, vars)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["leave"] }),
  });
}

Do not change anything else.
