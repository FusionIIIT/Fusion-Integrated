import { useEffect, useState } from "react";
import {
  Badge, Button, Card, Container, Group, Stack, Table, Text, Title
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { PageHeader } from "../../../ui/components/PageHeader";

export default function SubstitutionsPage() {
  const [requests, setRequests] = useState<any[]>([]);

  const fetchRequests = async () => {
    try {
      const res = await fetch("/api/v1/elm/substitutions");
      if (res.ok) setRequests(await res.json());
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchRequests();
  }, []);

  const handleRespond = async (id: number, action: "accept" | "decline") => {
    try {
      const res = await fetch(`/api/v1/elm/applications/${id}/substitute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action }),
      });
      if (res.ok) {
        notifications.show({ title: "Success", message: `Substitute request ${action}ed.` });
        fetchRequests();
      }
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <Container size="xl">
      <PageHeader
        title="Substitute Requests"
        subtitle="Review and respond to responsibility coverage requests from colleagues"
      />

      <Card shadow="sm" padding="md" withBorder>
        <Table highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Applicant (ID)</Table.Th>
              <Table.Th>Category</Table.Th>
              <Table.Th>Duration</Table.Th>
              <Table.Th>Reason</Table.Th>
              <Table.Th>Action</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {requests.map((r) => (
              <Table.Tr key={r.id}>
                <Table.Td>User #{r.user_id}</Table.Td>
                <Table.Td><Badge>{r.leave_category}</Badge></Table.Td>
                <Table.Td>{r.start_date} to {r.end_date} ({r.calculated_days} days)</Table.Td>
                <Table.Td>{r.reason}</Table.Td>
                <Table.Td>
                  <Group gap="xs">
                    <Button size="xs" color="green" onClick={() => handleRespond(r.id, "accept")}>
                      Accept
                    </Button>
                    <Button size="xs" color="red" variant="subtle" onClick={() => handleRespond(r.id, "decline")}>
                      Decline
                    </Button>
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
            {requests.length === 0 && (
              <Table.Tr>
                <Table.Td colSpan={5}>
                  <Text ta="center" c="dimmed" py="md">No pending substitute requests.</Text>
                </Table.Td>
              </Table.Tr>
            )}
          </Table.Tbody>
        </Table>
      </Card>
    </Container>
  );
}
