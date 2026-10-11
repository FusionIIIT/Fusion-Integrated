import { useEffect, useState } from "react";
import {
  Card, SimpleGrid, Text, Title, Stack, Badge, Group, Button, Table,
  TextInput, Select, Textarea, Checkbox, Tabs, Alert, Center, Loader,
} from "@mantine/core";
import { http, errorMessage } from "../../lib/http";

export default function LeavePage() {
  const [balances, setBalances] = useState<any[]>([]);
  const [myLeaves, setMyLeaves] = useState<any[]>([]);
  const [approvals, setApprovals] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Form states
  const [leaveType, setLeaveType] = useState("CL");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [reason, setReason] = useState("");
  const [stationLeave, setStationLeave] = useState(false);
  const [stationAddress, setStationAddress] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function loadData() {
    setLoading(true);
    Promise.all([
      http.get("/elm/balances"),
      http.get("/elm/applications"),
      http.get("/elm/approvals"),
    ])
      .then(([b, m, a]) => {
        setBalances(b.data);
        setMyLeaves(m.data);
        setApprovals(a.data);
      })
      .catch((e) => setError(errorMessage(e)))
      .finally(() => setLoading(false));
  }

  useEffect(() => { loadData(); }, []);

  async function handleApply(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await http.post("/elm/applications", {
        leave_type: leaveType, start_date: startDate, end_date: endDate,
        reason, station_leave: stationLeave, station_address: stationAddress,
      });
      setReason(""); setStartDate(""); setEndDate("");
      loadData();
    } catch (err) { setError(errorMessage(err)); }
    finally { setSubmitting(false); }
  }

  async function handleAction(id: number, action: string) {
    try {
      await http.post(`/elm/applications/${id}/action`, { action });
      loadData();
    } catch (err) { setError(errorMessage(err)); }
  }

  if (loading) return <Center h="50vh"><Loader /></Center>;

  return (
    <Stack gap="md" p="md">
      <Title order={2}>Employee Leave Management</Title>
      {error && <Alert color="red" onClose={() => setError(null)} withCloseButton>{error}</Alert>}

      <SimpleGrid cols={{ base: 2, sm: 3, md: 6 }}>
        {balances.map((b) => (
          <Card key={b.id} withBorder p="xs" radius="md">
            <Text fw={600} size="xs">{b.leave_type}</Text>
            <Text fw={700} size="lg" c="blue">{b.available_balance}</Text>
            <Text size="xs" c="dimmed">Avail / {b.allocated}</Text>
          </Card>
        ))}
      </SimpleGrid>

      <Tabs defaultValue="applications">
        <Tabs.List>
          <Tabs.Tab value="applications">My Applications</Tabs.Tab>
          <Tabs.Tab value="apply">Apply Leave</Tabs.Tab>
          <Tabs.Tab value="approvals">Approvals ({approvals.length})</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="applications" pt="sm">
          <Card withBorder p="sm">
            <Table striped highlightOnHover>
              <Table.Thead><Table.Tr><Table.Th>Type</Table.Th><Table.Th>Dates</Table.Th><Table.Th>Days</Table.Th><Table.Th>Status</Table.Th><Table.Th>Action</Table.Th></Table.Tr></Table.Thead>
              <Table.Tbody>
                {myLeaves.map((l) => (
                  <Table.Tr key={l.id}>
                    <Table.Td fw={600}>{l.leave_type}</Table.Td>
                    <Table.Td>{l.start_date} to {l.end_date}</Table.Td>
                    <Table.Td>{l.days_requested}</Table.Td>
                    <Table.Td><Badge color={l.status === "APPROVED" ? "green" : l.status === "REJECTED" ? "red" : "yellow"}>{l.status}</Badge></Table.Td>
                    <Table.Td>{l.status === "SUBMITTED" && <Button size="xs" color="red" variant="subtle" onClick={() => handleAction(l.id, "CANCEL")}>Cancel</Button>}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Card>
        </Tabs.Panel>

        <Tabs.Panel value="apply" pt="sm">
          <Card withBorder p="md" component="form" onSubmit={handleApply} maw={600}>
            <Stack gap="xs">
              <Select label="Leave Category" value={leaveType} onChange={(v) => setLeaveType(v || "CL")} data={["CL", "RH", "SCL", "EL", "VL", "COL"]} />
              <Group grow>
                <TextInput label="Start Date" type="date" required value={startDate} onChange={(e) => setStartDate(e.target.value)} />
                <TextInput label="End Date" type="date" required value={endDate} onChange={(e) => setEndDate(e.target.value)} />
              </Group>
              <Textarea label="Reason" required value={reason} onChange={(e) => setReason(e.target.value)} />
              <Checkbox label="Station Leave" checked={stationLeave} onChange={(e) => setStationLeave(e.currentTarget.checked)} />
              {stationLeave && <TextInput label="Station Address" value={stationAddress} onChange={(e) => setStationAddress(e.target.value)} />}
              <Button type="submit" loading={submitting} mt="xs">Submit Request</Button>
            </Stack>
          </Card>
        </Tabs.Panel>

        <Tabs.Panel value="approvals" pt="sm">
          <Card withBorder p="sm">
            <Table striped highlightOnHover>
              <Table.Thead><Table.Tr><Table.Th>Applicant</Table.Th><Table.Th>Type</Table.Th><Table.Th>Dates</Table.Th><Table.Th>Days</Table.Th><Table.Th>Status</Table.Th><Table.Th>Decision</Table.Th></Table.Tr></Table.Thead>
              <Table.Tbody>
                {approvals.map((a) => (
                  <Table.Tr key={a.id}>
                    <Table.Td>User #{a.user_id}</Table.Td>
                    <Table.Td fw={600}>{a.leave_type}</Table.Td>
                    <Table.Td>{a.start_date} to {a.end_date}</Table.Td>
                    <Table.Td>{a.days_requested}</Table.Td>
                    <Table.Td><Badge color="yellow">{a.status}</Badge></Table.Td>
                    <Table.Td>
                      <Group gap="xs">
                        <Button size="xs" color="green" onClick={() => handleAction(a.id, "APPROVE")}>Approve</Button>
                        <Button size="xs" color="red" variant="subtle" onClick={() => handleAction(a.id, "REJECT")}>Reject</Button>
                      </Group>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Card>
        </Tabs.Panel>
      </Tabs>
    </Stack>
  );
}
