import { Card, Container, Stack, Text } from "@mantine/core";
import { FaWallet } from "react-icons/fa";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useLeaveBalances } from "../api";
import type { LeaveBalance } from "../types";

export default function BalancesPage() {
  const { data, isPending, error } = useLeaveBalances();

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  const balances = (data ?? []) as LeaveBalance[];

  return (
    <Container size="xl">
      <PageHeader
        title="Leave Balances"
        subtitle="Your available leave quotas for the current year"
      />
      <Card padding="lg" withBorder>
        <DataTable<LeaveBalance>
          rows={balances}
          loading={isPending}
          rowKey={(r) => r.id}
          columns={[
            {
              key: "type",
              header: "Leave Type",
              render: (r) => (
                <Stack gap={0}>
                  <Text fw={600}>
                    {r.leave_type_name || `Type #${r.leave_type}`}
                  </Text>
                  {r.leave_type_code && (
                    <Text size="xs" c="dimmed">
                      {r.leave_type_code}
                    </Text>
                  )}
                </Stack>
              ),
            },
            {
              key: "balance",
              header: "Remaining Balance",
              render: (r) => <Text fw={600}>{r.balance} days</Text>,
            },
            {
              key: "year",
              header: "Year",
              render: (r) => r.year,
            },
          ]}
          empty={{
            icon: FaWallet,
            title: "No leave balances recorded",
            description: "No balance records exist for your account for this year.",
          }}
        />
      </Card>
    </Container>
  );
}
