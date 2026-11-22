import { useState } from "react";
import { Badge, Button, Card, Container, Group, Stack, Table, Text, TextInput, Title } from "@mantine/core";
import { useGateCheckIn, useGateCheckOut, useVisits } from "../api/hooks";

export default function GatePage() {
  const { data: visits } = useVisits();
  const checkIn = useGateCheckIn();
  const checkOut = useGateCheckOut();

  const [qrHash, setQrHash] = useState("");
  const [gateName, setGateName] = useState("Main Gate");

  const onScanCheckIn = () => {
    if (!qrHash) return;
    checkIn.mutate({ qr_code_hash: qrHash, gate_name: gateName });
    setQrHash("");
  };

  const onsite = visits?.filter((v) => v.status === "on_site") || [];

  return (
    <Container size="xl" py="md">
      <Stack gap="lg">
        <Title order={2}>Gate Scanner & Access Terminal</Title>

        <Card withBorder padding="md">
          <Title order={4} mb="sm">Fast QR Verification & Check-in</Title>
          <Group mb="sm">
            <TextInput
              label="QR Code Token / Hash"
              placeholder="Paste or scan QR hash"
              value={qrHash}
              onChange={(e) => setQrHash(e.target.value)}
              style={{ flex: 1 }}
            />
            <TextInput
              label="Gate Location"
              value={gateName}
              onChange={(e) => setGateName(e.target.value)}
            />
          </Group>
          <Button onClick={onScanCheckIn} loading={checkIn.isPending}>
            Process Check-in
          </Button>
        </Card>

        <Card withBorder padding="md">
          <Title order={4} mb="sm">Currently On-Campus Visitors ({onsite.length})</Title>
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Pass Number</Table.Th>
                <Table.Th>Visitor Name</Table.Th>
                <Table.Th>Phone</Table.Th>
                <Table.Th>Checked In At</Table.Th>
                <Table.Th>Actions</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {onsite.length === 0 ? (
                <Table.Tr>
                  <Table.Td colSpan={5}>
                    <Text ta="center" c="dimmed">No visitors currently on site.</Text>
                  </Table.Td>
                </Table.Tr>
              ) : (
                onsite.map((v) => (
                  <Table.Tr key={v.id}>
                    <Table.Td>{v.pass_number}</Table.Td>
                    <Table.Td>{v.visitor.first_name} {v.visitor.last_name}</Table.Td>
                    <Table.Td>{v.visitor.phone}</Table.Td>
                    <Table.Td>{v.check_in_time ? new Date(v.check_in_time).toLocaleTimeString() : "-"}</Table.Td>
                    <Table.Td>
                      <Button
                        size="xs"
                        color="red"
                        variant="light"
                        loading={checkOut.isPending}
                        onClick={() => checkOut.mutate(v.id)}
                      >
                        Check Out
                      </Button>
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
