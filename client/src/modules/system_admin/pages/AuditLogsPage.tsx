import { useEffect, useState } from "react";
import {
  Badge,
  Card,
  Code,
  Container,
  Group,
  Pagination,
  Table,
  Tabs,
  Text,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaSearch } from "react-icons/fa";

import { PageHeader } from "../../../ui/components/PageHeader";
import { adminApi } from "../api/client";
import type { FailedLoginLog, SystemAuditLog } from "../api/types";

export default function AuditLogsPage() {
  const [activeTab, setActiveTab] = useState<string | null>("audit");
  const [auditLogs, setAuditLogs] = useState<SystemAuditLog[]>([]);
  const [failedLogins, setFailedLogins] = useState<FailedLoginLog[]>([]);
  const [totalAudit, setTotalAudit] = useState(0);
  const [loading, setLoading] = useState(false);

  // Filters
  const [actionFilter, setActionFilter] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 25;

  const fetchData = () => {
    setLoading(true);
    Promise.all([
      adminApi.getAuditLogs({
        action: actionFilter || undefined,
        limit: pageSize,
        offset: (page - 1) * pageSize,
      }),
      adminApi.getFailedLogins(),
    ])
      .then(([auditRes, failedRes]) => {
        setAuditLogs(auditRes.results);
        setTotalAudit(auditRes.total);
        setFailedLogins(failedRes);
      })
      .catch((err) => {
        notifications.show({ color: "red", message: "Failed to load audit logs: " + String(err) });
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchData();
  }, [actionFilter, page]);

  return (
    <Container size="xl" py="lg">
      <PageHeader
        title="Audit Logs & Security Monitoring"
        subtitle="Immutable append-only record of administrative lifecycle operations and security authentication tracking."
      />

      <Tabs value={activeTab} onChange={setActiveTab}>
        <Tabs.List mb="md">
          <Tabs.Tab value="audit">Administrative Audit Trail ({totalAudit})</Tabs.Tab>
          <Tabs.Tab value="failed_logins">Failed Login Attempts ({failedLogins.length})</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="audit">
          <Card withBorder mb="md" padding="sm">
            <TextInput
              placeholder="Filter by action code (e.g. system_admin.user.add)..."
              leftSection={<FaSearch size={14} />}
              value={actionFilter}
              onChange={(e) => {
                setActionFilter(e.currentTarget.value);
                setPage(1);
              }}
              w={350}
            />
          </Card>

          <Card withBorder padding="md">
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Timestamp (UTC)</Table.Th>
                  <Table.Th>Actor ID</Table.Th>
                  <Table.Th>Action Code</Table.Th>
                  <Table.Th>Target ID</Table.Th>
                  <Table.Th>IP Address</Table.Th>
                  <Table.Th>Result</Table.Th>
                  <Table.Th>Context Data</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {auditLogs.map((log) => (
                  <Table.Tr key={log.id}>
                    <Table.Td>{new Date(log.timestamp).toLocaleString()}</Table.Td>
                    <Table.Td fw={500}>{log.actor_id}</Table.Td>
                    <Table.Td>
                      <Badge variant="outline" color="blue">
                        {log.action}
                      </Badge>
                    </Table.Td>
                    <Table.Td>{log.target_id || "—"}</Table.Td>
                    <Table.Td>{log.ip_address || "127.0.0.1"}</Table.Td>
                    <Table.Td>
                      <Badge color={log.result === "success" ? "green" : "red"}>{log.result}</Badge>
                    </Table.Td>
                    <Table.Td>
                      <Code block style={{ maxHeight: 60, overflowY: "auto", fontSize: "0.75rem" }}>
                        {JSON.stringify(log.context, null, 2)}
                      </Code>
                    </Table.Td>
                  </Table.Tr>
                ))}
                {auditLogs.length === 0 && !loading && (
                  <Table.Tr>
                    <Table.Td colSpan={7} style={{ textAlign: "center", padding: "2rem" }}>
                      <Text c="dimmed">No audit logs found.</Text>
                    </Table.Td>
                  </Table.Tr>
                )}
              </Table.Tbody>
            </Table>

            {totalAudit > pageSize && (
              <Group justify="center" mt="md">
                <Pagination total={Math.ceil(totalAudit / pageSize)} value={page} onChange={setPage} />
              </Group>
            )}
          </Card>
        </Tabs.Panel>

        <Tabs.Panel value="failed_logins">
          <Card withBorder padding="md">
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Attempted At</Table.Th>
                  <Table.Th>Username</Table.Th>
                  <Table.Th>IP Address</Table.Th>
                  <Table.Th>Reason / Failure Context</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {failedLogins.map((fl) => (
                  <Table.Tr key={fl.id}>
                    <Table.Td>{new Date(fl.attempted_at).toLocaleString()}</Table.Td>
                    <Table.Td fw={600} c="red">
                      {fl.username}
                    </Table.Td>
                    <Table.Td>{fl.ip_address || "127.0.0.1"}</Table.Td>
                    <Table.Td>{fl.reason || "Invalid credentials"}</Table.Td>
                  </Table.Tr>
                ))}
                {failedLogins.length === 0 && (
                  <Table.Tr>
                    <Table.Td colSpan={4} style={{ textAlign: "center", padding: "2rem" }}>
                      <Text c="dimmed">No failed logins recorded in current period.</Text>
                    </Table.Td>
                  </Table.Tr>
                )}
              </Table.Tbody>
            </Table>
          </Card>
        </Tabs.Panel>
      </Tabs>
    </Container>
  );
}
