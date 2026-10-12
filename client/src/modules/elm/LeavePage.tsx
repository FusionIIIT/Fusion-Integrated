import { useEffect, useState } from "react";
import {
  Card, SimpleGrid, Text, Title, Stack, Badge, Group, Button, Table,
  TextInput, Select, Textarea, Checkbox, Tabs, Alert, Center, Loader, Paper,
} from "@mantine/core";
import { http, errorMessage } from "../../lib/http";

export default function LeavePage() {
  const [balances, setBalances] = useState<any[]>([]);
  const [leaves, setLeaves] = useState<any[]>([]);
  const [pendingReviews, setPendingReviews] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusMessage, setStatusMessage] = useState<{ text: string; color: string } | null>(null);

  const [formType, setFormType] = useState("CL");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [justification, setJustification] = useState("");
  const [isStation, setIsStation] = useState(false);
  const [destAddress, setDestAddress] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  function refreshData() {
    setLoading(true);
    Promise.all([
      http.get("/elm/balances"),
      http.get("/elm/applications"),
      http.get("/elm/approvals"),
    ])
      .then(([bRes, lRes, aRes]) => {
        setBalances(bRes.data);
        setLeaves(lRes.data);
        setPendingReviews(aRes.data);
      })
      .catch((e) => setStatusMessage({ text: errorMessage(e), color: "red" }))
      .finally(() => setLoading(false));
  }

  useEffect(() => { refreshData(); }, []);

  async function onApply(e: React.FormEvent) {
    e.preventDefault();
    setIsSubmitting(true);
    setStatusMessage(null);
    try {
      await http.post("/elm/applications", {
        leave_type: formType, start_date: fromDate, end_date: toDate,
        reason: justification, station_leave: isStation, station_address: destAddress,
      });
      setJustification(""); setFromDate(""); setToDate("");
      setStatusMessage({ text: "Leave request submitted successfully!", color: "green" });
      refreshData();
    } catch (err) { setStatusMessage({ text: errorMessage(err), color: "red" }); }
    finally { setIsSubmitting(false); }
  }

  async function executeAction(id: number, actionName: string) {
    try {
      await http.post(`/elm/applications/${id}/action`, { action: actionName });
      refreshData();
    } catch (err) { setStatusMessage({ text: errorMessage(err), color: "red" }); }
  }

  if (loading) return <Center h="50vh"><Loader /></Center>;

  return (
    <Stack gap="md" p="md">
      <Group justify="space-between">
        <Title order={2}>Employee Leave Portal</Title>
        <Badge size="lg" color="blue" variant="filled">Active Session 2026</Badge>
      </Group>

      {statusMessage && (
        <Alert color={statusMessage.color} onClose={() => setStatusMessage(null)} withCloseButton>
          {statusMessage.text}
        </Alert>
      )}

      <SimpleGrid cols={{ base: 2, sm: 3, md: 6 }}>
        {balances.map((item) => (
          <Paper key={item.id} withBorder p="sm" radius="md" bg="gray.0">
            <Text fw={700} size="xs" c="dimmed">{item.leave_type}</Text>
            <Text fw={800} size="xl" c="blue.7">{item.remaining}</Text>
            <Text size="xs" c="gray.6">Avail of {item.allocated} days</Text>
          </Paper>
        ))}
      </SimpleGrid>

      <Tabs defaultValue="history">
        <Tabs.List>
          <Tabs.Tab value="history">My Leave Records</Tabs.Tab>
          <Tabs.Tab value="new_leave">New Request</Tabs.Tab>
          <Tabs.Tab value="reviews">Review Inbox ({pendingReviews.length})</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="history" pt="sm">
          <Card withBorder p="xs">
            <Table striped highlightOnHover>
              <Table.Thead><Table.Tr><Table.Th>Type</Table.Th><Table.Th>Period</Table.Th><Table.Th>Days</Table.Th><Table.Th>Status</Table.Th><Table.Th>Actions</Table.Th></Table.Tr></Table.Thead>
              <Table.Tbody>
                {leaves.map((l) => (
                  <Table.Tr key={l.id}>
                    <Table.Td fw={600}>{l.leave_type}</Table.Td>
                    <Table.Td>{l.start_date} → {l.end_date}</Table.Td>
                    <Table.Td>{l.days_count}</Table.Td>
                    <Table.Td><Badge color={l.status === "APPROVED" ? "green" : l.status === "REJECTED" ? "red" : "yellow"}>{l.status}</Badge></Table.Td>
                    <Table.Td>{l.status === "PENDING" && <Button size="xs" color="red" variant="light" onClick={() => executeAction(l.id, "WITHDRAW")}>Withdraw</Button>}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Card>
        </Tabs.Panel>

        <Tabs.Panel value="new_leave" pt="sm">
          <Card withBorder p="md" component="form" onSubmit={onApply} maw={550}>
            <Stack gap="xs">
              <Select label="Leave Category" value={formType} onChange={(val) => setFormType(val || "CL")} data={["CL", "RH", "SCL", "EL", "VL", "COL"]} />
              <Group grow>
                <TextInput label="Start Date" type="date" required value={fromDate} onChange={(e) => setFromDate(e.target.value)} />
                <TextInput label="End Date" type="date" required value={toDate} onChange={(e) => setToDate(e.target.value)} />
              </Group>
              <Textarea label="Reason / Purpose" required minRows={3} value={justification} onChange={(e) => setJustification(e.target.value)} />
              <Checkbox label="Traveling outside station" checked={isStation} onChange={(e) => setIsStation(e.currentTarget.checked)} />
              {isStation && <TextInput label="Station Contact / Address" value={destAddress} onChange={(e) => setDestAddress(e.target.value)} />}
              <Button type="submit" loading={isSubmitting} mt="xs">Submit Leave Request</Button>
            </Stack>
          </Card>
        </Tabs.Panel>

        <Tabs.Panel value="reviews" pt="sm">
          <Card withBorder p="xs">
            <Table striped highlightOnHover>
              <Table.Thead><Table.Tr><Table.Th>Applicant</Table.Th><Table.Th>Category</Table.Th><Table.Th>Duration</Table.Th><Table.Th>Days</Table.Th><Table.Th>Action</Table.Th></Table.Tr></Table.Thead>
              <Table.Tbody>
                {pendingReviews.map((r) => (
                  <Table.Tr key={r.id}>
                    <Table.Td>User #{r.user_id}</Table.Td>
                    <Table.Td fw={600}>{r.leave_type}</Table.Td>
                    <Table.Td>{r.start_date} → {r.end_date}</Table.Td>
                    <Table.Td>{r.days_count}</Table.Td>
                    <Table.Td>
                      <Group gap="xs">
                        <Button size="xs" color="teal" onClick={() => executeAction(r.id, "APPROVE")}>Approve</Button>
                        <Button size="xs" color="red" variant="subtle" onClick={() => executeAction(r.id, "REJECT")}>Reject</Button>
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
