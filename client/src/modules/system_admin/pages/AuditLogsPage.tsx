import { useState } from "react";
import {
  ActionIcon,
  Badge,
  Button,
  Card,
  Grid,
  Group,
  Modal,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Tooltip,
} from "@mantine/core";
import {
  FaDownload,
  FaEye,
  FaHistory,
  FaLock,
  FaSearch,
} from "react-icons/fa";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { downloadAuditCsv, useAuditLogs } from "../api/hooks";
import type { AuditLog } from "../api/types";

export default function AuditLogsPage() {
  const [filterActor, setFilterActor] = useState("");
  const [filterAction, setFilterAction] = useState("");
  const [filterResult, setFilterResult] = useState<string | null>(null);
  const [inspectLog, setInspectLog] = useState<AuditLog | null>(null);

  const { data: logs = [], isLoading } = useAuditLogs({
    actor: filterActor || undefined,
    action: filterAction || undefined,
    result: filterResult || undefined,
  });

  return (
    <Stack gap="lg">
      <PageHeader
        title="Immutable Audit & Compliance Trail"
        subtitle="Permanent, tamper-evident record of all Super Admin control plane actions (CFR-SA-017, BR-SA-025, BR-SA-033)"
        action={
          <Button
            leftSection={<FaDownload />}
            variant="outline"
            onClick={() => downloadAuditCsv()}
          >
            Export Compliance Report (CSV)
          </Button>
        }
      />

      <Card withBorder p="md" radius="md">
        <Grid mb="md" align="flex-end">
          <Grid.Col span={{ base: 12, sm: 4 }}>
            <TextInput
              placeholder="Filter by Actor Username..."
              leftSection={<FaSearch size={14} />}
              value={filterActor}
              onChange={(e) => setFilterActor(e.currentTarget.value)}
            />
          </Grid.Col>
          <Grid.Col span={{ base: 6, sm: 4 }}>
            <TextInput
              placeholder="Filter by Action (e.g. user.create)..."
              value={filterAction}
              onChange={(e) => setFilterAction(e.currentTarget.value)}
            />
          </Grid.Col>
          <Grid.Col span={{ base: 6, sm: 4 }}>
            <Select
              placeholder="Filter by Result"
              clearable
              data={[
                { value: "success", label: "Success" },
                { value: "failure", label: "Failure" },
              ]}
              value={filterResult}
              onChange={setFilterResult}
            />
          </Grid.Col>
        </Grid>

        <Table highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Timestamp</Table.Th>
              <Table.Th>Actor</Table.Th>
              <Table.Th>Action</Table.Th>
              <Table.Th>Target</Table.Th>
              <Table.Th>Result</Table.Th>
              <Table.Th>IP Address</Table.Th>
              <Table.Th style={{ textAlign: "right" }}>Inspect</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {logs.length === 0 ? (
              <Table.Tr>
                <Table.Td colSpan={7} style={{ textAlign: "center", padding: "40px 0" }}>
                  <Text c="dimmed">No audit log records matching criteria.</Text>
                </Table.Td>
              </Table.Tr>
            ) : (
              logs.map((l) => (
                <Table.Tr key={l.id}>
                  <Table.Td style={{ whiteSpace: "nowrap" }}>
                    <Text size="xs">
                      {new Date(l.timestamp).toLocaleString()}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Text size="sm" fw={600}>
                      {l.actor_username}
                    </Text>
                    <Text size="xs" c="dimmed">
                      ID #{l.actor_user_id}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Badge variant="light" size="sm">
                      {l.action}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Text size="xs">
                      {l.target_type ? `${l.target_type}:${l.target_id}` : "—"}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <StatusBadge status={l.result} />
                  </Table.Td>
                  <Table.Td>
                    <Text size="xs" c="dimmed">
                      {l.ip_address || "127.0.0.1"}
                    </Text>
                  </Table.Td>
                  <Table.Td style={{ textAlign: "right" }}>
                    <Tooltip label="View Audit Context">
                      <ActionIcon variant="subtle" color="blue" onClick={() => setInspectLog(l)}>
                        <FaEye size={14} />
                      </ActionIcon>
                    </Tooltip>
                  </Table.Td>
                </Table.Tr>
              ))
            )}
          </Table.Tbody>
        </Table>
      </Card>

      {/* Details Inspector Modal */}
      <Modal
        opened={!!inspectLog}
        onClose={() => setInspectLog(null)}
        title="Audit Event Details"
        size="lg"
      >
        {inspectLog && (
          <Stack gap="sm">
            <Group justify="space-between">
              <Text fw={600} size="sm">
                Event #{inspectLog.id} · {inspectLog.action}
              </Text>
              <StatusBadge status={inspectLog.result} />
            </Group>

            <Text size="xs" c="dimmed">
              Recorded at: {new Date(inspectLog.timestamp).toISOString()}
            </Text>

            {inspectLog.reason && (
              <Card withBorder p="xs" radius="sm">
                <Text size="xs" fw={600}>
                  Administrative Justification / Reason:
                </Text>
                <Text size="sm">{inspectLog.reason}</Text>
              </Card>
            )}

            <Text size="xs" fw={600} mt="xs">
              Context Metadata (JSON):
            </Text>
            <pre
              style={{
                background: "var(--mantine-color-gray-1)",
                padding: 12,
                borderRadius: 6,
                fontSize: 12,
                overflowX: "auto",
              }}
            >
              {JSON.stringify(inspectLog.details || {}, null, 2)}
            </pre>

            <Group justify="space-between" mt="md">
              <Group gap={4}>
                <FaLock size={12} color="gray" />
                <Text size="xs" c="dimmed">
                  Tamper-evident & non-deletable record
                </Text>
              </Group>
              <Button variant="default" onClick={() => setInspectLog(null)}>
                Close
              </Button>
            </Group>
          </Stack>
        )}
      </Modal>
    </Stack>
  );
}
