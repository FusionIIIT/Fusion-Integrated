import { useState, useEffect } from "react";
import {
  Alert, Badge, Card, Container, Group, Text, FaPrint, FaDownload,
  FaInfoCircle, Button,
} from "@mantine/core";
import { useLeaveHistory, useLeaveBalances } from "../api/hooks";
import { useNavigate } from "react-router-dom";
import type { LeaveHistoryEntry, LeaveBalance } from "../api/types";

/** EL-UC-013: Obtain Printable/Exportable Leave Application — Get a printable
 * or exportable representation of an accessible leave application. */
export default function PrintApplicationPage() {
  const navigate = useNavigate();
  const historyQuery = useLeaveHistory();
  const balancesQuery = useLeaveBalances();

  const history = historyQuery.data ?? [];
  const balances = balancesQuery.data?.balances ?? [];

  if (historyQuery.error) {
    return (
      <Container size="md">
        <ErrorState error={historyQuery.error} />
      </Container>
    );
  }

  // Select the most recent/application-specific application for printing
  const application = history.length > 0 ? history[history.length - 1] : null;

  if (!application) {
    return (
      <Container size="md">
        <PageHeader title="Print Leave Application" />
        <Alert variant="light" color="gray" icon={<FaInfoCircle />}>
          No leave application found to print. Submit a leave application first.
        </Alert>
      </Container>
    );
  }

  // Build printable data
  const printData = {
    application_id: application.pk,
    employee_user_id: application.employee_user_id,
    leave_category: {
      code: application.leave_category_code,
      label: application.leave_category_code, // Would get label from category lookup
    },
    requested_start: application.requested_start,
    requested_end: application.requested_end,
    purpose_reason: application.purpose_reason || "Not specified",
    station_leave: application.station_leave,
    station_details: application.station_details || "Not applicable",
    status: application.status,
    submitted_at: application.submitted_at
      ? new Date(application.submitted_at).toLocaleDateString()
      : "Not specified",
    balances_as_of: new Date().toLocaleDateString(),
  };

  // Add current balance info
  const currentBalance = balances.find(
    (b) => b.leave_category_code === application.leave_category_code
  );
  if (currentBalance) {
    printData.current_balance = {
      available: currentBalance.available_days,
      entitlement: currentBalance.entitlement_per_year,
      used: currentBalance.used_per_year,
    };
  }

  return (
    <Container size="md">
      <PageHeader title="Print Leave Application" />

      <Card padding="lg">
        <Group gap="sm">
          <Text fw={600}>Leave Application Details</Text>

          <Group gap="sm" md>
            <Group>
              <Text>Application ID:</Text>
              <Text fw>{application.pk}</Text>
            </Group>
            <Group>
              <Text>Leave Category:</Text>
              <Text fw>{application.leave_category_code}</Text>
            </Group>
            <Group>
              <Text>Requested Period:</Text>
              <Text fw>{application.requested_start} - {application.requested_end}</Text>
            </Group>
            <Group>
              <Text>Purpose / Reason:</Text>
              <Text fw>{application.purpose_reason || "Not specified"}</Text>
            </Group>
          </Group>

          {application.station_leave && (
            <Group>
              <Text>Station Leave (Outside Jabalpur):</Text>
              <Text fw>{application.station_details || "Details not provided"}</Text>
            </Group>
          )}

          <Group>
            <Text>Status:</Text>
            <Badge
              color={
                application.status === "approved" ? "green"
                : application.status === "rejected" ? "red"
                : application.status === "withdrawn" ? "orange"
                : "blue"
              }
            >
              {application.status}
            </Badge>
            <Text size="xs" c="dimmed">
              Submitted: {application.submitted_at
                ? new Date(application.submitted_at).toLocaleDateString()
                : "—"}
            </Text>
          </Group>
        </Group>

        {/* Current Balance Summary */}
        {printData.currentBalance && (
          <Group gap="sm" mt="sm">
            <Text fw={600}>Current Leave Balance</Text>
            <Group>
              <Text>Available:</Text>
              <Text fw>{printData.currentBalance.available}</Text>
            </Group>
            <Group>
              <Text>Entitlement/Year:</Text>
              <Text fw>{printData.currentBalance.entitlement}</Text>
            </Group>
            <Group>
              <Text>Used (Current Year):</Text>
              <Text fw>{printData.currentBalance.used}</Text>
            </Group>
          </Group>
        )}

        {/* Action buttons */}
        <Group gap="sm" justify="flex-end" mt="sm">
          <Button
            onClick={() => navigator.print()}
            disabled={false}
            type="button"
          >
            Print
          </Button>
          <Button
            onClick={() => window.print()}
            disabled={false}
            type="button"
            style={{ marginLeft: 8 }}
          >
            Export as PDF
          </Button>
        </Group>
      </Card>
    </Container>
  );
}

/** Placeholder ErrorState component */
function ErrorState({ error }: { error: any }) {
  return (
    <Card padding="lg" color="red">
      <Text fw={600} mb="xs">Error</Text>
      <Text c="red">{error?.message || error || "Unknown error"}</Text>
    </Card>
  );
}