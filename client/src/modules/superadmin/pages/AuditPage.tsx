import { useState } from "react";
import {
  Badge, Card, Container, Group, Loader, Select, Stack, Text, TextInput,
} from "@mantine/core";
import { TbFileText, TbSearch } from "react-icons/tb";

import { DataTable, type Column } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAuditLogs } from "../api/hooks";
import type { AuditLog } from "../api/types";

const RESULT_COLOR: Record<string, string> = { SUCCESS: "green", FAILURE: "red" };

const ACTION_GROUPS: Record<string, string> = {
  "archival.user.created": "Archival",
  "archival.user.restored": "Archival",
  "archival.user.finalized": "Archival",
  "purge.requested": "Purge",
  "purge.approved": "Purge",
  "purge.rejected": "Purge",
  "purge.executed": "Purge",
  "purge.expired": "Purge",
  "policy.superseded": "Policy",
};

const COLUMNS: Column<AuditLog>[] = [
  {
    key: "timestamp",
    header: "Time",
    render: (r) => new Date(r.timestamp).toLocaleString(),
  },
  { key: "actor_username", header: "Actor" },
  { key: "actor_role", header: "Role" },
  {
    key: "action",
    header: "Action",
    render: (r) => (
      <Stack gap={2}>
        <Text size="xs" c="dimmed">{ACTION_GROUPS[r.action] ?? "Other"}</Text>
        <Text size="sm" fw={500}>{r.action}</Text>
      </Stack>
    ),
  },
  { key: "target_id", header: "Target" },
  { key: "target_type", header: "Target Type" },
  {
    key: "result",
    header: "Result",
    render: (r) => (
      <Badge color={RESULT_COLOR[r.result] ?? "gray"} variant="light">{r.result}</Badge>
    ),
  },
  { key: "reason", header: "Reason" },
];

export default function AuditPage() {
  const [search, setSearch] = useState("");
  const [action, setAction] = useState<string | null>(null);

  const filters: Record<string, unknown> = {};
  if (search) filters["actor_username"] = search;
  if (action) filters["action"] = action;

  const { data, isPending, error } = useAuditLogs(filters);

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  return (
    <Container size="xl">
      <PageHeader
        title="Audit Logs"
        subtitle="Immutable compliance event log — all governance actions recorded permanently"
      />

      <Group mb="md" gap="sm">
        <TextInput
          aria-label="Search by actor username"
          placeholder="Search by actor username…"
          leftSection={<TbSearch size={14} />}
          value={search}
          onChange={(e) => setSearch(e.currentTarget.value)}
          style={{ flex: 1 }}
        />
        <Select
          placeholder="Filter by action group…"
          data={["archival.user.created", "archival.user.restored", "purge.requested",
            "purge.approved", "purge.executed", "policy.superseded"]}
          value={action}
          onChange={setAction}
          clearable
          style={{ width: 240 }}
        />
      </Group>

      <Card padding="lg" withBorder>
        {isPending && <Loader mt="sm" />}
        {!isPending && (
          <DataTable<AuditLog>
            rows={data?.results ?? []}
            loading={false}
            columns={COLUMNS}
            rowKey={(r) => r.id}
            empty={{
              icon: TbFileText,
              title: "No audit events found",
              description: "No audit events match the current filters.",
            }}
          />
        )}
      </Card>

      <Text size="xs" c="dimmed" mt="sm">
        {data?.count ?? 0} total events · Audit log entries are permanent and immutable
      </Text>
    </Container>
  );
}
