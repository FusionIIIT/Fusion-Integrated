import { useState } from "react";
import {
  Badge,
  Card,
  Code,
  Container,
  Group,
  NumberInput,
  Paper,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import {
  FaArchive,
  FaFileAlt,
  FaPaperPlane,
  FaRandom,
  FaShieldAlt,
  FaTrash,
} from "react-icons/fa";

import { DataTable, type Column } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useGovernanceAuditLogs, useGovernanceUsage } from "../api/hooks";
import type { FileAuditLog } from "../api/types";

const ACTION_COLORS: Record<string, string> = {
  FILE_CREATED: "green",
  DRAFT_UPDATED: "blue",
  DRAFT_DISCARDED: "red",
  FILE_FORWARDED: "indigo",
  FILE_RETURNED: "orange",
  FILE_ARCHIVED: "teal",
};

export default function GovernancePage() {
  const [fileIdFilter, setFileIdFilter] = useState<number | string>("");

  const numFileId = typeof fileIdFilter === "number" && fileIdFilter > 0 ? fileIdFilter : null;
  const { data: metrics, isPending: loadingMetrics, error: metricsError } = useGovernanceUsage();
  const { data: logs, isPending: loadingLogs, error: logsError } = useGovernanceAuditLogs(numFileId);

  const columns: Column<FileAuditLog>[] = [
    {
      key: "timestamp",
      header: "Timestamp",
      render: (row) => (
        <Text size="xs" c="dimmed">
          {new Date(row.timestamp).toLocaleString()}
        </Text>
      ),
    },
    {
      key: "action",
      header: "Action",
      render: (row) => (
        <Badge
          size="sm"
          variant="light"
          color={ACTION_COLORS[row.action] ?? "gray"}
        >
          {row.action}
        </Badge>
      ),
    },
    {
      key: "file_id",
      header: "File ID",
      render: (row) => (
        <Text size="sm" fw={600}>
          {row.file_id ?? "—"}
        </Text>
      ),
    },
    {
      key: "actor",
      header: "Actor",
      render: (row) => (
        <Text size="sm">
          {row.actor_username} ({row.actor_role || "User"} [ID: {row.actor_user_id}])
        </Text>
      ),
    },
    {
      key: "details",
      header: "Details",
      render: (row) => (
        <Code block style={{ maxHeight: 80, overflow: "auto", fontSize: 11 }}>
          {JSON.stringify(row.details, null, 2)}
        </Code>
      ),
    },
  ];

  return (
    <Container size="xl" py="lg">
      <PageHeader
        title="FTS Governance & Audit"
        subtitle="System usage overview, file status breakdown, and immutable lifecycle audit trail"
      />

      <Stack gap="xl">
        {metricsError && <ErrorState error={metricsError} />}

        {/* Metrics Grid */}
        <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="md">
          <Card withBorder padding="md">
            <Group justify="space-between">
              <div>
                <Text size="xs" c="dimmed" fw={700} tt="uppercase">
                  Total Files
                </Text>
                <Text fw={700} size="xl">
                  {loadingMetrics ? "…" : (metrics?.total_files ?? 0)}
                </Text>
              </div>
              <FaFileAlt size={24} color="gray" />
            </Group>
          </Card>

          <Card withBorder padding="md">
            <Group justify="space-between">
              <div>
                <Text size="xs" c="dimmed" fw={700} tt="uppercase">
                  Active (Circulated)
                </Text>
                <Text fw={700} size="xl" c="blue">
                  {loadingMetrics ? "…" : (metrics?.circulated_files ?? 0)}
                </Text>
              </div>
              <FaPaperPlane size={24} color="#228be6" />
            </Group>
          </Card>

          <Card withBorder padding="md">
            <Group justify="space-between">
              <div>
                <Text size="xs" c="dimmed" fw={700} tt="uppercase">
                  Drafts
                </Text>
                <Text fw={700} size="xl" c="yellow">
                  {loadingMetrics ? "…" : (metrics?.draft_files ?? 0)}
                </Text>
              </div>
              <FaFileAlt size={24} color="#fab005" />
            </Group>
          </Card>

          <Card withBorder padding="md">
            <Group justify="space-between">
              <div>
                <Text size="xs" c="dimmed" fw={700} tt="uppercase">
                  Archived Files
                </Text>
                <Text fw={700} size="xl" c="teal">
                  {loadingMetrics ? "…" : (metrics?.archived_files ?? 0)}
                </Text>
              </div>
              <FaArchive size={24} color="#12b886" />
            </Group>
          </Card>

          <Card withBorder padding="md">
            <Group justify="space-between">
              <div>
                <Text size="xs" c="dimmed" fw={700} tt="uppercase">
                  Total Movements
                </Text>
                <Text fw={700} size="xl" c="indigo">
                  {loadingMetrics ? "…" : (metrics?.total_movements ?? 0)}
                </Text>
              </div>
              <FaRandom size={24} color="#4c6ef5" />
            </Group>
          </Card>

          <Card withBorder padding="md">
            <Group justify="space-between">
              <div>
                <Text size="xs" c="dimmed" fw={700} tt="uppercase">
                  Discarded Drafts
                </Text>
                <Text fw={700} size="xl" c="red">
                  {loadingMetrics ? "…" : (metrics?.discarded_drafts ?? 0)}
                </Text>
              </div>
              <FaTrash size={24} color="#fa5252" />
            </Group>
          </Card>
        </SimpleGrid>

        {/* Audit Trail Section */}
        <Stack gap="md">
          <Group justify="space-between" align="center">
            <Title order={4}>Immutable Audit Trail</Title>
            <NumberInput
              placeholder="Filter by File ID..."
              value={fileIdFilter}
              onChange={(val) => setFileIdFilter(val)}
              min={1}
              style={{ width: 220 }}
            />
          </Group>

          {logsError && <ErrorState error={logsError} />}

          <Paper withBorder>
            <DataTable
              rows={logs ?? []}
              columns={columns}
              loading={loadingLogs}
              rowKey={(r) => r.id}
              empty={{
                icon: FaShieldAlt,
                title: "No audit logs found",
                description: "No security or movement events match the selected criteria.",
              }}
            />
          </Paper>
        </Stack>
      </Stack>
    </Container>
  );
}
