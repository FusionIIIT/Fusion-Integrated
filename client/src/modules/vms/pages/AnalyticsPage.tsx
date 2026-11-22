import { Badge, Card, Container, Group, SimpleGrid, Stack, Text } from "@mantine/core";
import { FaCalendarDay, FaCheckCircle, FaExclamationTriangle, FaUserCheck } from "react-icons/fa";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAnalytics, useAuditLogs } from "../api/hooks";
import type { GateCheckLog } from "../api/types";

export default function AnalyticsPage() {
  const { data: metrics, error: mError } = useAnalytics();
  const { data: logs, isPending: logsPending, error: lError } = useAuditLogs();

  if (mError || lError) {
    return (
      <Container size="xl">
        <ErrorState error={mError || lError} />
      </Container>
    );
  }

  const m = metrics ?? {
    total_today: 0,
    onsite_now: 0,
    approved: 0,
    pending: 0,
    rejected: 0,
    overstays: 0,
    completed: 0,
  };

  return (
    <Container size="xl">
      <Stack gap="lg">
        <PageHeader
          title="Visitor Analytics & Operational Audit Log"
          subtitle="Real-time campus visitor counts, overstay tracking, and gate audit trail."
        />

        {/* Metric Cards */}
        <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }}>
          <Card withBorder padding="md" radius="md">
            <Group justify="space-between">
              <div>
                <Text size="xs" c="dimmed" fw={700}>
                  TODAY'S VISITS
                </Text>
                <Text fw={700} size="xl">
                  {m.total_today}
                </Text>
              </div>
              <FaCalendarDay size={24} color="var(--mantine-color-blue-6)" />
            </Group>
          </Card>
          <Card withBorder padding="md" radius="md">
            <Group justify="space-between">
              <div>
                <Text size="xs" c="dimmed" fw={700}>
                  CURRENTLY ON-SITE
                </Text>
                <Text fw={700} size="xl" c="green">
                  {m.onsite_now}
                </Text>
              </div>
              <FaUserCheck size={24} color="var(--mantine-color-green-6)" />
            </Group>
          </Card>
          <Card withBorder padding="md" radius="md">
            <Group justify="space-between">
              <div>
                <Text size="xs" c="dimmed" fw={700}>
                  COMPLETED EXITS
                </Text>
                <Text fw={700} size="xl">
                  {m.completed}
                </Text>
              </div>
              <FaCheckCircle size={24} color="var(--mantine-color-teal-6)" />
            </Group>
          </Card>
          <Card withBorder padding="md" radius="md">
            <Group justify="space-between">
              <div>
                <Text size="xs" c="dimmed" fw={700}>
                  OVERSTAYS DETECTED
                </Text>
                <Text fw={700} size="xl" c={m.overstays > 0 ? "red" : "gray"}>
                  {m.overstays}
                </Text>
              </div>
              <FaExclamationTriangle
                size={24}
                color={m.overstays > 0 ? "var(--mantine-color-red-6)" : "gray"}
              />
            </Group>
          </Card>
        </SimpleGrid>

        <Card withBorder padding="md" radius="md">
          <Text fw={600} mb="sm">
            Recent Gate & Zone Audit Events
          </Text>
          <DataTable
            loading={logsPending}
            rows={logs ?? []}
            rowKey={(l) => l.id}
            empty={{ title: "No gate check logs recorded yet." }}
            columns={[
              {
                key: "timestamp",
                header: "Timestamp",
                render: (l: GateCheckLog) => new Date(l.timestamp).toLocaleString(),
              },
              {
                key: "gate",
                header: "Gate / Location",
                render: (l: GateCheckLog) => l.gate_name,
              },
              {
                key: "action",
                header: "Action",
                render: (l: GateCheckLog) => (
                  <Badge
                    color={
                      l.action === "CHECK_IN"
                        ? "green"
                        : l.action === "CHECK_OUT"
                        ? "blue"
                        : l.action === "OVERRIDE"
                        ? "yellow"
                        : "red"
                    }
                  >
                    {l.action}
                  </Badge>
                ),
              },
              {
                key: "operator",
                header: "Operator ID",
                render: (l: GateCheckLog) => (l.operator_id ? `#${l.operator_id}` : "System"),
              },
              {
                key: "override",
                header: "Override Justification",
                render: (l: GateCheckLog) =>
                  l.is_override ? (
                    <Text size="xs" c="orange">
                      {l.override_reason}
                    </Text>
                  ) : (
                    <Text size="xs" c="dimmed">
                      Standard Verification
                    </Text>
                  ),
              },
            ]}
          />
        </Card>
      </Stack>
    </Container>
  );
}
