import { useState } from "react";
import {
  Badge,
  Card,
  Container,
  Group,
  Select,
  Stack,
  Text,
  TextInput,
} from "@mantine/core";
import { FaHistory, FaSearch } from "react-icons/fa";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAuditLogs } from "../api/hooks";
import type { AuditLog } from "../api/types";

const RESULT_OPTIONS = [
  { value: "", label: "All Results" },
  { value: "success", label: "Success" },
  { value: "failure", label: "Failure" },
  { value: "denied", label: "Denied" },
];

export default function AuditLogsPage() {
  const [actorSearch, setActorSearch] = useState("");
  const [resultFilter, setResultFilter] = useState<string | null>("");

  const { data, isPending, error } = useAuditLogs({
    actor_username: actorSearch.trim() || undefined,
    result: resultFilter || undefined,
    limit: 100,
  });

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  const logs: AuditLog[] = Array.isArray(data)
    ? data
    : Array.isArray((data as any)?.results)
    ? (data as any).results
    : [];

  const getResultBadge = (res: string) => {
    switch (res) {
      case "success":
        return (
          <Badge color="green" variant="light" size="sm">
            Success
          </Badge>
        );
      case "denied":
        return (
          <Badge color="red" variant="light" size="sm">
            Denied
          </Badge>
        );
      case "failure":
      default:
        return (
          <Badge color="orange" variant="light" size="sm">
            Failure
          </Badge>
        );
    }
  };

  return (
    <Container size="xl">
      <PageHeader
        title="Security & Audit Trail"
        subtitle="Append-only timeline of administrative operations, delegations, and access attempts"
      />

      <Card padding="md" mb="md" withBorder radius="md">
        <Group>
          <TextInput
            placeholder="Search by actor username..."
            leftSection={<FaSearch size={12} />}
            value={actorSearch}
            onChange={(e) => setActorSearch(e.currentTarget.value)}
            style={{ flex: 1 }}
          />
          <Select
            placeholder="Result Filter"
            data={RESULT_OPTIONS}
            value={resultFilter}
            onChange={setResultFilter}
            clearable
          />
        </Group>
      </Card>

      <Card padding="lg" withBorder radius="md">
        <DataTable<AuditLog>
          rows={logs}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={950}
          columns={[
            {
              key: "timestamp",
              header: "Timestamp",
              render: (r) => (
                <Text size="xs">
                  {new Date(r.timestamp).toLocaleString()}
                </Text>
              ),
            },
            {
              key: "actor",
              header: "Actor",
              render: (r) => (
                <Stack gap={0}>
                  <Text fw={600} size="sm">
                    {r.actor_username}
                  </Text>
                  <Text size="xs" c="dimmed">
                    User #{r.actor_id}
                  </Text>
                </Stack>
              ),
            },
            {
              key: "action",
              header: "Action",
              render: (r) => (
                <Badge variant="outline" size="sm" color="blue">
                  {r.action}
                </Badge>
              ),
            },
            {
              key: "target",
              header: "Target",
              render: (r) => (
                <Text size="xs">
                  {r.target_role_code
                    ? `Role: ${r.target_role_code}`
                    : r.target_user_id
                    ? `User #${r.target_user_id}`
                    : "—"}
                </Text>
              ),
            },
            {
              key: "ip_address",
              header: "IP Address",
              render: (r) => (
                <Text size="xs" ff="monospace">
                  {r.ip_address}
                </Text>
              ),
            },
            {
              key: "result",
              header: "Result",
              render: (r) => getResultBadge(r.result),
            },
            {
              key: "reason",
              header: "Remark / Justification",
              render: (r) => (
                <Text size="xs" lineClamp={2} c="dimmed">
                  {r.reason || "—"}
                </Text>
              ),
            },
          ]}
          empty={{
            icon: FaHistory,
            title: "No Audit Logs",
            description: "No security or administrative audit records match your filters.",
          }}
        />
      </Card>
    </Container>
  );
}
