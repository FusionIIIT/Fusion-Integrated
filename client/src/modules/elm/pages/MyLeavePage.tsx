import { useState } from "react";
import {
  Button, Card, Container, Stack, Text,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaUserCheck } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useLeaveBalances, useLeaveApplications, useCreateLeaveApplication } from "../api/hooks";
import type { LeaveType, LeaveBalance, LeaveApplication } from "../api/types";

export default function MyLeavePage() {
  const [leaveType, setLeaveType] = useState<LeaveType | null>(null);
  const [startDate, setStartDate] = useState<Date | null>(null);
  const [endDate, setEndDate] = useState<Date | null>(null);
  const [isHalfDay, setIsHalfDay] = useState(false);
  const [reason, setReason] = useState<string>("");
  const { data: balances, isPending: balancesPending, error: balancesError } = useLeaveBalances();
  const { data: applications, isPending: applicationsPending, error: applicationsError } = useLeaveApplications();
  const createApplicationMutation = useCreateLeaveApplication();

  if (balancesError) return <Container size="xl"><ErrorState error={balancesError} /></Container>;
  if (applicationsError) return <Container size="xl"><ErrorState error={applicationsError} /></Container>;

  function applyForLeave() {
    if (!leaveType || !startDate || !endDate || !reason) {
      notifications.show({
        color: "red", title: "Invalid input",
        message: "Please fill in all required fields.",
      });
      return;
    }

    createApplicationMutation.mutate(
      { leave_type: leaveType.code, start_date: startDate.toLocaleDateString("en-CA"), end_date: endDate.toLocaleDateString("en-CA"), is_half_day: isHalfDay, reason },
      {
        onSuccess: () => notifications.show({
          color: "green", title: "Leave application submitted",
          message: "Your leave application has been submitted successfully.",
        }),
        onError: (e) => notifications.show({
          color: "red", title: "Could not submit leave application", message: errorMessage(e),
        }),
      },
    );
  }

  return (
    <Container size="xl">
      <PageHeader
        title="My Leave"
        subtitle="Your leave balances and applications"
      />
      <Card padding="lg">
        <Stack gap="md">
          <Text fw={600}>Leave Balances</Text>
          <DataTable<LeaveBalance>
            rows={(balances ?? []) as LeaveBalance[]}
            loading={balancesPending}
            rowKey={(r) => r.year}
            minWidth={400}
            columns={[
              { key: "employee", header: "Employee ID" },
              { key: "balance", header: "Entitled Days" },
            ]}
            empty={{
              icon: FaUserCheck,
              title: "No leave balances available",
              description: "Your leave balances will appear here.",
            }}
          />
        </Stack>
      </Card>

      <Card padding="lg">
        <Stack gap="md">
          <Text fw={600}>Leave Applications</Text>
          <DataTable<LeaveApplication>
            rows={(applications ?? []) as LeaveApplication[]}
            loading={applicationsPending}
            rowKey={(r) => r.id}
            minWidth={400}
            columns={[
              { key: "id", header: "ID" },
              { key: "leave_type", header: "Leave Type" },
              { key: "start_date", header: "Start Date",
                render: (r) => r.start_date ? new Date(r.start_date).toLocaleDateString() : "—" },
              { key: "end_date", header: "End Date",
                render: (r) => r.end_date ? new Date(r.end_date).toLocaleDateString() : "—" },
              { key: "status", header: "Status",
                render: (r) => <StatusBadge status={r.status} /> },
            ]}
            empty={{
              icon: FaUserCheck,
              title: "No leave applications available",
              description: "Your leave applications will appear here.",
            }}
          />
        </Stack>
      </Card>

      <Card padding="lg">
        <Stack gap="md">
          <Text fw={600}>Apply for Leave</Text>
          <select value={leaveType?.code ?? ""} onChange={(e) => setLeaveType({ code: e.target.value } as LeaveType)}>
            {balances?.map((balance) => (
              <option key={balance.leave_type} value={balance.leave_type}>{balance.leave_type}</option>
            ))}
          </select>
          <input type="date" value={startDate?.toLocaleDateString("en-CA").split('T')[0] ?? ""} onChange={(e) => setStartDate(new Date(e.target.value))} />
          <input type="date" value={endDate?.toLocaleDateString("en-CA").split('T')[0] ?? ""} onChange={(e) => setEndDate(new Date(e.target.value))} />
          <label>
            Half Day
            <input type="checkbox" checked={isHalfDay} onChange={(e) => setIsHalfDay(e.target.checked)} />
          </label>
          <textarea value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Reason for leave" />
          <Button size="xs" onClick={applyForLeave}>Submit</Button>
        </Stack>
      </Card>
    </Container>
  );
}
