import React, { useEffect, useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Loader,
  Table,
  Text,
  Title,
  Alert,
} from "@mantine/core";
import { leaveApi, type LeaveRequest } from "../api/leaveApi";

function getStatusBadge(status: string) {
  switch (status) {
    case "APPROVED":
      return <Badge color="green">Approved</Badge>;
    case "RECOMMENDED":
      return <Badge color="blue">Recommended</Badge>;
    case "PENDING_APPROVAL":
      return <Badge color="yellow">Pending</Badge>;
    case "REJECTED":
      return <Badge color="red">Rejected</Badge>;
    case "CANCELLED":
      return <Badge color="gray">Cancelled</Badge>;
    default:
      return <Badge color="gray">{status}</Badge>;
  }
}

export default function LeaveHistoryPage() {
  const [requests, setRequests] = useState<LeaveRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionError, setActionError] = useState<string | null>(null);

  const fetchRequests = () => {
    leaveApi
      .getMyRequests()
      .then((data) => {
        setRequests(data);
        setLoading(false);
      })
      .catch((err) => {
        setActionError(err.message || "Failed to load requests");
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchRequests();
  }, []);

  const handleCancel = async (id: number) => {
    if (!window.confirm("Are you sure you want to cancel this leave application?")) return;
    try {
      await leaveApi.cancelLeaveRequest(id);
      fetchRequests();
    } catch (err: any) {
      setActionError(err.message || "Failed to cancel leave request");
    }
  };

  if (loading) {
    return (
      <Container size="lg" py="xl">
        <Group justify="center">
          <Loader size="lg" />
        </Group>
      </Container>
    );
  }

  return (
    <Container size="lg" py="xl">
      <Title order={2} mb="lg">
        My Leave Applications
      </Title>

      {actionError && (
        <Alert color="red" mb="md" onClose={() => setActionError(null)} withCloseButton>
          {actionError}
        </Alert>
      )}

      <Card withBorder radius="md">
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>ID</Table.Th>
              <Table.Th>Type</Table.Th>
              <Table.Th>Duration</Table.Th>
              <Table.Th>Dates</Table.Th>
              <Table.Th>Reason</Table.Th>
              <Table.Th>Station Leave</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Action</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {requests.length === 0 ? (
              <Table.Tr>
                <Table.Td colSpan={8} align="center">
                  <Text c="dimmed">No leave applications found.</Text>
                </Table.Td>
              </Table.Tr>
            ) : (
              requests.map((req) => (
                <Table.Tr key={req.id}>
                  <Table.Td fw={500}>#{req.id}</Table.Td>
                  <Table.Td>{req.leave_type_code}</Table.Td>
                  <Table.Td>{req.duration_days} d</Table.Td>
                  <Table.Td>
                    {req.start_date} {req.start_date !== req.end_date ? `to ${req.end_date}` : ""}
                  </Table.Td>
                  <Table.Td>{req.reason}</Table.Td>
                  <Table.Td>
                    {req.is_station_leave ? (
                      <Badge color="orange" size="xs">
                        Yes ({req.station_start_date} - {req.station_end_date})
                      </Badge>
                    ) : (
                      "No"
                    )}
                  </Table.Td>
                  <Table.Td>{getStatusBadge(req.status)}</Table.Td>
                  <Table.Td>
                    {["DRAFT", "PENDING_APPROVAL", "RECOMMENDED"].includes(req.status) && (
                      <Button
                        size="xs"
                        variant="subtle"
                        color="red"
                        onClick={() => handleCancel(req.id)}
                      >
                        Cancel
                      </Button>
                    )}
                  </Table.Td>
                </Table.Tr>
              ))
            )}
          </Table.Tbody>
        </Table>
      </Card>
    </Container>
  );
}
