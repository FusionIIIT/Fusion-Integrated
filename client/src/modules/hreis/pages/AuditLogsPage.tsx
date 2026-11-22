import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  Paper,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { FaShieldAlt } from "react-icons/fa";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAuditLogs } from "../api/hooks";
import type { HrAuditLog } from "../api/types";

export default function AuditLogsPage() {
  const { data: logs, isPending, error } = useAuditLogs();
  const [detailLog, setDetailLog] = useState<HrAuditLog | null>(null);

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  return (
    <Container size="xl" py="md">
      <PageHeader
        title="Immutable Audit & Compliance Logs"
        subtitle="Cryptographically tracked, append-only record of all HR lifecycle transactions (BR-HR-025, AFR-087)"
      />

      <Card padding="lg" withBorder radius="md">
        <DataTable<HrAuditLog>
          rows={logs ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={900}
          empty={{
            icon: FaShieldAlt,
            title: "No audit events recorded",
            description: "No HR transactions have occurred yet.",
          }}
          columns={[
            {
              key: "timestamp",
              header: "Timestamp",
              render: (r) => (
                <Text size="xs" c="dimmed">
                  {new Date(r.timestamp).toLocaleString()}
                </Text>
              ),
            },
            {
              key: "actor",
              header: "Actor",
              render: (r) => (
                <div>
                  <Text size="sm" fw={600}>
                    {r.actor_username}
                  </Text>
                  <Text size="xs" c="dimmed">
                    #{r.actor_id}
                  </Text>
                </div>
              ),
            },
            {
              key: "role",
              header: "Role",
              render: (r) => (
                <Badge variant="outline" color="gray" size="sm">
                  {r.actor_role?.toUpperCase()}
                </Badge>
              ),
            },
            {
              key: "action",
              header: "Action Performed",
              render: (r) => (
                <Badge color="blue" variant="light" size="sm">
                  {r.action}
                </Badge>
              ),
            },
            {
              key: "entity",
              header: "Resource Entity",
              render: (r) => (
                <Text size="xs">
                  {r.entity_type} #{r.entity_id}
                </Text>
              ),
            },
            {
              key: "ip_address",
              header: "Source IP",
              render: (r) => <Text size="xs" c="dimmed">{r.ip_address || "127.0.0.1"}</Text>,
            },
            {
              key: "actions",
              header: "Payload",
              render: (r) => (
                <Button size="xs" variant="subtle" onClick={() => setDetailLog(r)}>
                  Inspect
                </Button>
              ),
            },
          ]}
        />
      </Card>

      {/* Inspect Details Modal */}
      <Modal
        opened={detailLog != null}
        onClose={() => setDetailLog(null)}
        title="Audit Transaction Metadata"
        size="md"
      >
        {detailLog && (
          <Stack gap="sm">
            <Group justify="space-between">
              <Text size="sm" c="dimmed">Action:</Text>
              <Badge color="blue">{detailLog.action}</Badge>
            </Group>
            <Group justify="space-between">
              <Text size="sm" c="dimmed">Actor:</Text>
              <Text size="sm" fw={600}>{detailLog.actor_username} (ID: {detailLog.actor_id})</Text>
            </Group>
            <Group justify="space-between">
              <Text size="sm" c="dimmed">Timestamp:</Text>
              <Text size="sm">{new Date(detailLog.timestamp).toLocaleString()}</Text>
            </Group>
            <Paper withBorder p="md" radius="sm">
              <Title order={6} mb="xs">Details JSON</Title>
              <pre style={{ fontSize: "12px", whiteSpace: "pre-wrap", margin: 0 }}>
                {JSON.stringify(detailLog.details, null, 2)}
              </pre>
            </Paper>
          </Stack>
        )}
      </Modal>
    </Container>
  );
}
