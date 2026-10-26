import { Container } from "@mantine/core";
import { PageHeader } from "../../ui/components/PageHeader";

import { ApplyLeaveForm } from "./components/ApplyLeaveForm";
import { HolidayCalendarView } from "./components/HolidayCalendarView";
import { LeaveAdminView } from "./components/LeaveAdminView";
import { LeaveApprovalsView } from "./components/LeaveApprovalsView";
import { LeaveBalancesView } from "./components/LeaveBalancesView";
import { MyRequestsView } from "./components/MyRequestsView";
import { SubstituteTasksView } from "./components/SubstituteTasksView";

interface LeavePageProps {
  view: "apply" | "mine" | "balances" | "substitute" | "approvals" | "calendar" | "admin";
}

const titles: Record<LeavePageProps["view"], { title: string; subtitle: string }> = {
  apply: { title: "Apply Leave", subtitle: "Submit a new leave application with optional substitute coverage" },
  mine: { title: "My Requests", subtitle: "Track, withdraw, cancel, extend, or submit resumption for your leave requests" },
  balances: { title: "Leave Balances", subtitle: "View entitlement breakdown, availed days, and available balances" },
  substitute: { title: "Substitute Tasks", subtitle: "Review and respond to pending substitute requests" },
  approvals: { title: "Leave Approvals", subtitle: "Review and action leave applications awaiting your approval" },
  calendar: { title: "Holiday Calendar", subtitle: "Published institutional closed holidays, restricted holidays, and vacations" },
  admin: { title: "Leave Admin", subtitle: "Institutional year-end processing, SLA threshold evaluation, and record synchronization" },
};

export default function LeavePage({ view }: LeavePageProps) {
  const { title, subtitle } = titles[view];

  return (
    <Container size="xl" py="md">
      <PageHeader title={title} subtitle={subtitle} />

      {view === "apply" && <ApplyLeaveForm />}
      {view === "mine" && <MyRequestsView />}
      {view === "balances" && <LeaveBalancesView />}
      {view === "substitute" && <SubstituteTasksView />}
      {view === "approvals" && <LeaveApprovalsView />}
      {view === "calendar" && <HolidayCalendarView />}
      {view === "admin" && <LeaveAdminView />}
    </Container>
  );
}
