import { useAuth } from "../../../auth/AuthProvider";

export function useElmRole() {
  const { session, can } = useAuth();
  return {
    userId: session?.user.id,
    activeRole: session?.active_role ?? "",
    isEmployee: can("elm.leave.apply"),
    canReview: can("elm.leave.review"),
    canProcess: can("elm.leave.process"),
    canSanction: can("elm.leave.sanction"),
    canViewAll: can("elm.leave.view_all"),
    canManage: can("elm.config.manage"),
    canManageCalendar: can("elm.calendar.manage"),
    canManageRecords: can("elm.record.manage"),
    canRunYearEnd: can("elm.leave.year_end"),
    canWithdraw: can("elm.leave.withdraw"),
  };
}