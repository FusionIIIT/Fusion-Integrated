import React, { useEffect, useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  SimpleGrid,
  Stack,
  Table,
  Text,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCalendarAlt, FaPlus, FaUndo } from "react-icons/fa";
import { useNavigate } from "react-router-dom";

import { http } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";

interface LeaveBalance {
  id: number;
  category: string;
  credited: string;
  availed: string;
  balance: string;
  lapsed: string;
  year: number;
}

interface LeaveRequest {
  id: number;
  category: string;
  start_date: string;
  end_date: string;
  half_day: string;
  requested_days: string;
  purpose: string;
  status: string;
  station_leave: boolean;
  substitute_status: string;
  created_at: string;
}

export default function LeaveDashboardPage() {
  const navigate = useNavigate();
  const [balances, setBalances] = useState<LeaveBalance[]>([]);
  const [requests, setRequests] = useState<LeaveRequest[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      setLoading(true);
      const [bRes, rRes] = await Promise.all([
        http.get<LeaveBalance[]>("/api/v1/leave/balances/"),
        http.get<LeaveRequest[]>("/api/v1/leave/applications/"),
      ]);
      setBalances(bRes.data);
      setRequests(rRes.data);
    } catch {
      notifications.show({
        color: "red",
        title: "Error",
        message: "Failed to load leave dashboard data",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleWithdraw = async (id: number) => {
    try {
      await http.delete(`/api/v1/leave/applications/${id}/`);
      notifications.show({ color: "green", title: "Success", message: "Request withdrawn" });
      loadData();
    } catch {
      notifications.show({ color: "red", title: "Error", message: "Failed to withdraw request" });
    }
  };

  const handleCancel = async (id: number) => {
    try {
      await http.post(`/api/v1/leave/applications/${id}/cancel/`);
      notifications.show({
        color: "green",
        title: "Success",
        message: "Cancellation request submitted",
      });
      loadData();
    } catch {
      notifications.show({ color: "red", title: "Error", message: "Failed to cancel leave" });
    }
  };

  const statusColor = (status: string) => {
    switch (status) {
      case "approved":
        return "green";
      case "rejected":
        return "red";
      case "withdrawn":
      case "cancelled":
        return "gray";
      default:
        return "blue";
    }
  };

  return (
    <Container size="xl" py="lg">
      <Stack gap="lg">
        <PageHeader
          title="Leave Management"
          description="View your leave balances, history, and status of applications"
          icon={<FaCalendarAlt size={22} />}
          actions={
            <Button
              leftSection={<FaPlus />}
              onClick={() => navigate("/leave/apply")}
            >
              Apply for Leave
            </Button>
          }
        />

        <Title order={3}>Leave Balances</Title>
        <SimpleGrid cols={{ base: 1, sm: 3, md: 6 }}>
          {balances.map((b) => (
            <Card key={b.category} shadow="xs" padding="md" radius="md" withBorder>
              <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
                {b.category}
              </Text>
              <Text fz="xl" fw={700} my="xs">
                {b.balance} days
              </Text>
              <Text size="xs" c="dimmed">
                Credited: {b.credited} | Availed: {b.availed}
              </Text>
            </Card>
          ))}
        </SimpleGrid>

        <Title order={3} mt="md">
          My Leave History
        </Title>
        <Card shadow="xs" padding="md" radius="md" withBorder>
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Category</Table.Th>
                <Table.Th>Dates</Table.Th>
                <Table.Th>Days</Table.Th>
                <Table.Th>Purpose</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Actions</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {requests.length === 0 ? (
                <Table.Tr>
                  <Table.Td colSpan={6} style={{ textAlign: "center" }}>
                    {loading ? "Loading..." : "No leave requests found."}
                  </Table.Td>
                </Table.Tr>
              ) : (
                requests.map((r) => (
                  <Table.Tr key={r.id}>
                    <Table.Td>
                      <Badge variant="outline">{r.category}</Badge>
                      {r.station_leave && (
                        <Badge size="xs" color="indigo" ml="xs">
                          Station
                        </Badge>
                      )}
                    </Table.Td>
                    <Table.Td>
                      {r.start_date} to {r.end_date}
                    </Table.Td>
                    <Table.Td>{r.requested_days}</Table.Td>
                    <Table.Td>{r.purpose}</Table.Td>
                    <Table.Td>
                      <Badge color={statusColor(r.status)}>
                        {r.status.replace(/_/g, " ")}
                      </Badge>
                    </Table.Td>
                    <Table.Td>
                      <Group gap="xs">
                        {r.status.startsWith("awaiting_") && (
                          <Button
                            size="xs"
                            variant="light"
                            color="red"
                            onClick={() => handleWithdraw(r.id)}
                          >
                            Withdraw
                          </Button>
                        )}
                        {r.status === "approved" && (
                          <Button
                            size="xs"
                            variant="light"
                            color="orange"
                            leftSection={<FaUndo size={12} />}
                            onClick={() => handleCancel(r.id)}
                          >
                            Cancel
                          </Button>
                        )}
                      </Group>
                    </Table.Td>
                  </Table.Tr>
                ))
              )}
            </Table.Tbody>
          </Table>
        </Card>
      </Stack>
    </Container>
  );
}
