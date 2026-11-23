import { Badge, Paper, Table, Text, Title } from "@mantine/core";
import { useEffect, useState } from "react";
import { http } from "../../../lib/http";

interface LeaveApplication {
  id: number;
  leave_type: number;
  leave_type_name?: string;
  start_date: string;
  end_date: string;
  status: string;
  created_at: string;
}

export default function LeaveHistory({ refreshKey }: { refreshKey?: number }) {
  const [applications, setApplications] = useState<LeaveApplication[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    http
      .get<any>("/leave/applications/")
      .then((res) => {
        const raw: any = res.data; const data = Array.isArray(raw) ? raw : (raw?.results ?? []);
        setApplications(data);
      })
      .catch((err) => {
        console.error("Failed to load leave history", err);
      })
      .finally(() => {
        setLoading(false);
      });
  }, [refreshKey]);

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case "approved":
        return "green";
      case "rejected":
        return "red";
      default:
        return "yellow";
    }
  };

  return (
    <Paper withBorder p="md" radius="sm">
      <Title order={4} mb="sm">
        My Leave Applications
      </Title>
      {loading ? (
        <Text size="sm" c="dimmed">
          Loading applications...
        </Text>
      ) : applications.length === 0 ? (
        <Text size="sm" c="dimmed">
          No leave applications found.
        </Text>
      ) : (
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>ID</Table.Th>
              <Table.Th>Type</Table.Th>
              <Table.Th>Duration</Table.Th>
              <Table.Th>Status</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {applications.map((app) => (
              <Table.Tr key={app.id}>
                <Table.Td>#{app.id}</Table.Td>
                <Table.Td>{app.leave_type_name || `Type ${app.leave_type}`}</Table.Td>
                <Table.Td>
                  {app.start_date} to {app.end_date}
                </Table.Td>
                <Table.Td>
                  <Badge color={getStatusColor(app.status)}>{app.status}</Badge>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}
    </Paper>
  );
}

