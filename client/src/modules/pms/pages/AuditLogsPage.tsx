import { useState } from "react";
import {
  Badge,
  Card,
  Container,
  Group,
  Paper,
  Text,
  TextInput,
} from "@mantine/core";
import { FaSearch } from "react-icons/fa";

import { type Column, DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAuditLogs } from "../api/hooks";
import type { PatentAuditLog } from "../api/types";
import { StatusBadge } from "../components/StatusBadge";

export default function AuditLogsPage() {
  const [appId, setAppId] = useState<string>("");
  const [actionType, setActionType] = useState<string>("");

  const { data, isPending, error } = useAuditLogs({
    application_id: appId ? Number(appId) : undefined,
    action_type: actionType || undefined,
  });

  const columns: Column<PatentAuditLog>[] = [
    {
      key: "created_at",
      header: "Timestamp",
      render: (row) => (
        <Text size="xs">{new Date(row.created_at).toLocaleString()}</Text>
      ),
    },
    {
      key: "application_id",
      header: "Application ID",
      render: (row) => (
        <Text size="xs" fw={600}>
          App #{row.application_id}
        </Text>
      ),
    },
    {
      key: "action_type",
      header: "Action Performed",
      render: (row) => (
        <Badge variant="outline" size="sm">
          {row.action_type.replace(/_/g, " ").toUpperCase()}
        </Badge>
      ),
    },
    {
      key: "actor_role",
      header: "Actor Role & ID",
      render: (row) => (
        <Group gap="xs">
          <Badge size="xs" color="blue">
            {row.actor_role.toUpperCase()}
          </Badge>
          <Text size="xs" c="dimmed">
            (User #{row.user_id})
          </Text>
        </Group>
      ),
    },
    {
      key: "state_transition",
      header: "State Transition",
      render: (row) =>
        row.previous_state && row.new_state ? (
          <Group gap="xs">
            <StatusBadge status={row.previous_state} />
            <Text size="xs">→</Text>
            <StatusBadge status={row.new_state} />
          </Group>
        ) : (
          <Text size="xs" c="dimmed">
            No state change
          </Text>
        ),
    },
    {
      key: "ip_address",
      header: "IP Address",
      render: (row) => (
        <Text size="xs" c="dimmed">
          {row.ip_address || "127.0.0.1"}
        </Text>
      ),
    },
  ];

  return (
    <Container size="xl" py="lg">
      <PageHeader
        title="Compliance & Security Audit Log"
        subtitle="Immutable audit trail capturing every state transition, authorization decision, and prosecution event (ADR-0010)."
      />

      <Paper p="md" mb="md" withBorder>
        <Group>
          <TextInput
            placeholder="Filter by Application ID..."
            leftSection={<FaSearch />}
            value={appId}
            onChange={(e) => setAppId(e.target.value)}
            style={{ width: 220 }}
          />
          <TextInput
            placeholder="Filter by Action Type..."
            leftSection={<FaSearch />}
            value={actionType}
            onChange={(e) => setActionType(e.target.value)}
            style={{ width: 240 }}
          />
        </Group>
      </Paper>

      {error && <ErrorState error={error} />}

      <Card withBorder p={0}>
        <DataTable
          columns={columns}
          rows={data?.results ?? []}
          loading={isPending}
          rowKey={(row) => row.id}
          empty={{
            title: "No audit records found",
            description: "No compliance audit log events match query criteria.",
          }}
        />
      </Card>
    </Container>
  );
}
