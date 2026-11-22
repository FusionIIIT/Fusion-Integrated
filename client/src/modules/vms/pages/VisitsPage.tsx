import { useState } from "react";
import { Badge, Button, Card, Container, Group, Stack, Table, Text, TextInput, Title } from "@mantine/core";
import { useCreateVisit, useVisits } from "../api/hooks";

export default function VisitsPage() {
  const { data: visits, isLoading, isError, error } = useVisits();
  const createVisit = useCreateVisit();

  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [idNumber, setIdNumber] = useState("");
  const [purpose, setPurpose] = useState("");

  const handleCreate = () => {
    if (!firstName || !phone || !purpose) return;
    const now = new Date();
    const end = new Date(now.getTime() + 4 * 3600 * 1000);

    createVisit.mutate({
      first_name: firstName,
      last_name: lastName,
      phone,
      email: email || "guest@example.com",
      id_type: "aadhaar",
      id_number: idNumber || "123412341234",
      host_user_id: 1,
      purpose,
      valid_from: now.toISOString(),
      valid_to: end.toISOString(),
    });
  };

  return (
    <Container size="xl" py="md">
      <Stack gap="lg">
        <Title order={2}>Visitor Management — My Visits</Title>

        <Card withBorder padding="md">
          <Title order={4} mb="sm">Pre-register a New Visitor</Title>
          <Group mb="sm">
            <TextInput label="First Name" placeholder="Ramesh" value={firstName} onChange={(e) => setFirstName(e.target.value)} />
            <TextInput label="Last Name" placeholder="Sharma" value={lastName} onChange={(e) => setLastName(e.target.value)} />
            <TextInput label="Phone" placeholder="9876543210" value={phone} onChange={(e) => setPhone(e.target.value)} />
            <TextInput label="Email" placeholder="guest@example.com" value={email} onChange={(e) => setEmail(e.target.value)} />
            <TextInput label="ID Number" placeholder="Aadhaar / ID" value={idNumber} onChange={(e) => setIdNumber(e.target.value)} />
            <TextInput label="Purpose" placeholder="Official Meeting" value={purpose} onChange={(e) => setPurpose(e.target.value)} />
          </Group>
          <Button onClick={handleCreate} loading={createVisit.isPending}>
            Submit Visit Request
          </Button>
        </Card>

        {isLoading && <Text>Loading visits...</Text>}
        {isError && <Text c="red">Error loading visits: {String(error)}</Text>}

        {visits && (
          <Card withBorder padding="md">
            <Title order={4} mb="sm">Requested & Active Visits</Title>
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Pass Number</Table.Th>
                  <Table.Th>Visitor Name</Table.Th>
                  <Table.Th>Phone</Table.Th>
                  <Table.Th>Purpose</Table.Th>
                  <Table.Th>Status</Table.Th>
                  <Table.Th>Valid To</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {visits.map((v) => (
                  <Table.Tr key={v.id}>
                    <Table.Td>{v.pass_number}</Table.Td>
                    <Table.Td>{v.visitor.first_name} {v.visitor.last_name}</Table.Td>
                    <Table.Td>{v.visitor.phone}</Table.Td>
                    <Table.Td>{v.purpose}</Table.Td>
                    <Table.Td>
                      <Badge color={v.status === "on_site" ? "green" : v.status === "approved" ? "blue" : "gray"}>
                        {v.status}
                      </Badge>
                    </Table.Td>
                    <Table.Td>{new Date(v.valid_to).toLocaleDateString()}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Card>
        )}
      </Stack>
    </Container>
  );
}
