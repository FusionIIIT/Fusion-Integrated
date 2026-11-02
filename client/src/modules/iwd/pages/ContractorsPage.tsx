import { useEffect, useState } from "react";
import { Badge, Paper, Stack, Table, Text, Title } from "@mantine/core";

type Contractor = {
  id: number; name: string; registration_number: string;
  contact_person: string; phone: string; email: string;
  specialization: string; is_active: boolean;
};

export default function ContractorsPage() {
  const [contractors, setContractors] = useState<Contractor[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/v1/iwd/contractors/")
      .then((r) => r.json())
      .then((data) => { setContractors(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  if (loading) return <Text>Loading contractors...</Text>;

  return (
    <Stack gap="md" p="md">
      <Title order={2}>Registered Contractors</Title>
      <Paper shadow="xs" withBorder>
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Name</Table.Th><Table.Th>Reg. No.</Table.Th>
              <Table.Th>Contact Person</Table.Th><Table.Th>Phone</Table.Th>
              <Table.Th>Email</Table.Th><Table.Th>Specialization</Table.Th>
              <Table.Th>Status</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {contractors.map((c) => (
              <Table.Tr key={c.id}>
                <Table.Td>{c.name}</Table.Td>
                <Table.Td>{c.registration_number}</Table.Td>
                <Table.Td>{c.contact_person}</Table.Td>
                <Table.Td>{c.phone}</Table.Td>
                <Table.Td>{c.email}</Table.Td>
                <Table.Td>{c.specialization || "—"}</Table.Td>
                <Table.Td>
                  <Badge color={c.is_active ? "green" : "gray"}>
                    {c.is_active ? "Active" : "Inactive"}
                  </Badge>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
        {contractors.length === 0 && <Text ta="center" c="dimmed" p="md">No contractors registered.</Text>}
      </Paper>
    </Stack>
  );
}

