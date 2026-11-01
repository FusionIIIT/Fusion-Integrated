import { useState } from "react";
import {
  Stack,
  Table,
  Badge,
  Text,
  Button,
  Paper,
  Group,
  Loader,
  Alert,
  TextInput,
  Select,
  Modal,
  Code,
  ActionIcon,
  Tooltip,
} from "@mantine/core";
import { FaSearch, FaEye } from "react-icons/fa";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAuditLogs } from "../api/hooks";
import type { AuditLogItem } from "../api/types";

export default function AuditLogsPage() {
  const [search, setSearch] = useState("");
  const [actionFilter, setActionFilter] = useState<string>("all");
  const [resultFilter, setResultFilter] = useState<string>("all");
  const [selectedLog, setSelectedLog] = useState<AuditLogItem | null>(null);

  const filters = {
    search: search || undefined,
    action: actionFilter === "all" ? undefined : actionFilter,
    result: resultFilter === "all" ? undefined : resultFilter,
  };

  const { data, isLoading, error } = useAuditLogs(filters);

  const getResultBadge = (result: string) => {
    if (result === "SUCCESS" || result === "success") {
      return <Badge color="green">Success</Badge>;
    }
    if (result === "REJECTED" || result === "rejected") {
      return <Badge color="orange">Rejected</Badge>;
    }
    return <Badge color="red">Failure</Badge>;
  };

  const formatAction = (action: string) => {
    return action
      .split("_")
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(" ");
  };

  return (
    <Stack gap="lg">
      <PageHeader
        title="Audit Logs"
        subtitle="Append-only, immutable record of all administrative operations (BR-SA-024)"
      />

      {/* Filter Toolbar */}
      <Paper withBorder p="md" radius="md">
        <Group justify="space-between">
          <Group>
            <TextInput
              leftSection={<FaSearch size={14} />}
              placeholder="Search target user or description..."
              value={search}
              onChange={(e) => setSearch(e.currentTarget.value)}
              w={260}
            />
            <Select
              placeholder="Action"
              data={[
                { value: "all", label: "All Actions" },
                { value: "user_create", label: "User Create" },
                { value: "user_update", label: "User Update" },
                { value: "user_deactivate", label: "User Deactivate" },
                { value: "user_reactivate", label: "User Reactivate" },
                { value: "role_assign", label: "Role Assign" },
                { value: "role_reassign", label: "Role Reassign" },
                { value: "role_revoke", label: "Role Revoke" },
                { value: "role_extend", label: "Role Extend" },
                { value: "user_archive", label: "User Archive" },
                { value: "user_restore", label: "User Restore" },
                { value: "purge_request", label: "Purge Request" },
                { value: "purge_authorize", label: "Purge Authorize" },
                { value: "config_update", label: "Config Update" },
              ]}
              value={actionFilter}
              onChange={(val) => setActionFilter(val ?? "all")}
              w={180}
            />
            <Select
              placeholder="Result"
              data={[
                { value: "all", label: "All Results" },
                { value: "SUCCESS", label: "Success" },
                { value: "FAILURE", label: "Failure" },
                { value: "REJECTED", label: "Rejected" },
              ]}
              value={resultFilter}
              onChange={(val) => setResultFilter(val ?? "all")}
              w={140}
            />
          </Group>
          <Text size="sm" c="dimmed">
            {data ? `${data.count} event(s) recorded` : "Loading..."}
          </Text>
        </Group>
      </Paper>

      {isLoading && (
        <Stack align="center" justify="center" p="xl">
          <Loader />
          <Text c="dimmed">Loading audit events...</Text>
        </Stack>
      )}

      {error && (
        <Alert color="red" title="Error">
          Failed to load audit logs.
        </Alert>
      )}

      {data && (
        <Paper withBorder radius="md">
          <Table verticalSpacing="sm" striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Timestamp (UTC)</Table.Th>
                <Table.Th>Actor</Table.Th>
                <Table.Th>Action</Table.Th>
                <Table.Th>Target</Table.Th>
                <Table.Th>Result</Table.Th>
                <Table.Th>Reason / Summary</Table.Th>
                <Table.Th style={{ width: 80, textAlign: "center" }}>Details</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {data.results.map((log) => (
                <Table.Tr key={log.id}>
                  <Table.Td>
                    <Text size="xs" ff="monospace">
                      {new Date(log.timestamp).toLocaleString()}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Text fw={500} size="sm">
                      {log.actor_username}
                    </Text>
                    <Text size="xs" c="dimmed">
                      {log.actor_role} • {log.ip_address || "Internal"}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Badge variant="light" color="blue">
                      {formatAction(log.action)}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    {log.target_user ? (
                      <Text size="sm" fw={500}>
                        {log.target_user}
                      </Text>
                    ) : log.target_role ? (
                      <Text size="sm">{log.target_role}</Text>
                    ) : (
                      <Text size="xs" c="dimmed">—</Text>
                    )}
                  </Table.Td>
                  <Table.Td>{getResultBadge(log.result)}</Table.Td>
                  <Table.Td>
                    <Text size="sm" lineClamp={1}>
                      {log.reason_or_context || "—"}
                    </Text>
                  </Table.Td>
                  <Table.Td style={{ textAlign: "center" }}>
                    <Tooltip label="View Full Event Details">
                      <ActionIcon
                        variant="subtle"
                        color="blue"
                        onClick={() => setSelectedLog(log)}
                      >
                        <FaEye size={14} />
                      </ActionIcon>
                    </Tooltip>
                  </Table.Td>
                </Table.Tr>
              ))}
              {data.results.length === 0 && (
                <Table.Tr>
                  <Table.Td colSpan={7} style={{ textAlign: "center", padding: "2rem" }}>
                    <Text c="dimmed">No audit log records match query.</Text>
                  </Table.Td>
                </Table.Tr>
              )}
            </Table.Tbody>
          </Table>
        </Paper>
      )}

      {/* Log Detail Modal */}
      {selectedLog && (
        <Modal
          opened={Boolean(selectedLog)}
          onClose={() => setSelectedLog(null)}
          title={`Audit Event #${selectedLog.id}: ${formatAction(selectedLog.action)}`}
          size="lg"
        >
          <Stack gap="sm">
            <Group justify="space-between">
              <div>
                <Text size="xs" c="dimmed">Actor</Text>
                <Text fw={500}>{selectedLog.actor_username} ({selectedLog.actor_role})</Text>
              </div>
              <div>
                <Text size="xs" c="dimmed">Timestamp</Text>
                <Text size="sm">{new Date(selectedLog.timestamp).toUTCString()}</Text>
              </div>
              <div>
                <Text size="xs" c="dimmed">Status</Text>
                {getResultBadge(selectedLog.result)}
              </div>
            </Group>

            <Group justify="space-between">
              <div>
                <Text size="xs" c="dimmed">IP Address</Text>
                <Text size="sm">{selectedLog.ip_address || "127.0.0.1"}</Text>
              </div>
              <div>
                <Text size="xs" c="dimmed">Target Entity</Text>
                <Text size="sm">{selectedLog.target_user || selectedLog.target_role || "System Control Plane"}</Text>
              </div>
            </Group>

            <div>
              <Text size="xs" c="dimmed">Reason / Justification</Text>
              <Text size="sm">{selectedLog.reason_or_context || "None specified"}</Text>
            </div>

            <div>
              <Text size="xs" c="dimmed" mb={4}>Structured Metadata (Immutable JSON)</Text>
              <Code block style={{ maxHeight: 250, overflowY: "auto" }}>
                {JSON.stringify(selectedLog.metadata, null, 2)}
              </Code>
            </div>

            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => setSelectedLog(null)}>
                Close
              </Button>
            </Group>
          </Stack>
        </Modal>
      )}
    </Stack>
  );
}
