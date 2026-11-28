import { useCallback, useEffect, useState } from "react";
import {
  Alert, Badge, Button, Card, Container, Grid, Group, NumberInput, Select,
  Stack, Table, Text, TextInput, Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { getBalances, getRequests, requestAction, submitLeave } from "../api";
import type { LeaveBalance, LeaveRequest } from "../api";

const categories = ["CL", "RH", "SCL", "EL", "COL", "VL"];

export default function ElmMinePage() {
  const [balances, setBalances] = useState<LeaveBalance[]>([]);
  const [requests, setRequests] = useState<LeaveRequest[]>([]);
  const [category, setCategory] = useState<string | null>("CL");
  const [startsOn, setStartsOn] = useState("");
  const [endsOn, setEndsOn] = useState("");
  const [part, setPart] = useState<string | null>("");
  const [reason, setReason] = useState("");
  const [substituteId, setSubstituteId] = useState<number | "">("");
  const [stationDetails, setStationDetails] = useState("");
  const [busy, setBusy] = useState(false);
  const refresh = useCallback(async () => {
    try {
      const [b, r] = await Promise.all([getBalances(), getRequests()]);
      setBalances(b);
      setRequests(r);
    } catch (error) {
      notifications.show({ color: "red", title: "Could not load leave records", message: errorMessage(error) });
    }
  }, []);
  useEffect(() => { void refresh(); }, [refresh]);

  async function submit() {
    if (!category || !startsOn || !endsOn || !reason.trim()) return;
    setBusy(true);
    try {
      await submitLeave({
        category, starts_on: startsOn, ends_on: endsOn, reason,
        cl_part: part || "", substitute_user_id: substituteId || null,
        station_leave: Boolean(stationDetails.trim()), station_details: stationDetails,
      });
      notifications.show({ color: "green", title: "Leave request submitted", message: "The request is in the configured workflow." });
      setReason(""); setSubstituteId(""); setStationDetails("");
      await refresh();
    } catch (error) {
      notifications.show({ color: "red", title: "Could not submit leave", message: errorMessage(error) });
    } finally { setBusy(false); }
  }


  return (
    <Container size="xl">
      <PageHeader title="My Leave" subtitle="Balances, applications, and recorded decisions" />
      <Grid mb="md">
        {balances.map((b) => (
          <Grid.Col key={b.category} span={{ base: 6, sm: 4, md: 2 }}>
            <Card padding="md"><Text size="sm" c="dimmed">{b.category} balance</Text>
              <Text fw={700} size="xl">{b.spendable} <Text span size="xs" c="dimmed">days available</Text></Text>
              <Text size="xs" c="dimmed">{b.pending} pending · {b.entitlement} annual</Text>
            </Card>
          </Grid.Col>
        ))}
      </Grid>
      <Grid align="flex-start">
        <Grid.Col span={{ base: 12, md: 5 }}>
          <Card padding="lg">
            <Text fw={600} mb="md">Apply for leave</Text>
            <Stack>
              <Select label="Leave category" data={categories} value={category} onChange={setCategory} />
              <Group grow>
                <TextInput type="date" label="From" value={startsOn} onChange={(e) => setStartsOn(e.currentTarget.value)} />
                <TextInput type="date" label="Through" value={endsOn} onChange={(e) => setEndsOn(e.currentTarget.value)} />
              </Group>
              {category === "CL" && <Select label="CL portion (optional)" data={[{ value: "", label: "Full day" }, { value: "first", label: "First half" }, { value: "second", label: "Second half" }]} value={part} onChange={setPart} />}
              <Textarea label="Purpose / reason" minRows={3} value={reason} onChange={(e) => setReason(e.currentTarget.value)} />
              <NumberInput label="Substitute employee ID (when required)" min={1} value={substituteId} onChange={(value) => setSubstituteId(typeof value === "number" ? value : "")} />
              <TextInput label="Station Leave details (if outside Jabalpur)" value={stationDetails} onChange={(e) => setStationDetails(e.currentTarget.value)} />
              <Button onClick={() => void submit()} loading={busy} disabled={!category || !startsOn || !endsOn || !reason.trim()}>Submit request</Button>
            </Stack>
          </Card>
        </Grid.Col>
        <Grid.Col span={{ base: 12, md: 7 }}>
          <Card padding="lg">
            <Text fw={600} mb="md">Request history</Text>
            {requests.length ? <Table.ScrollContainer minWidth={680}><Table striped highlightOnHover>
              <Table.Thead><Table.Tr><Table.Th>Category</Table.Th><Table.Th>Dates</Table.Th><Table.Th>Days</Table.Th><Table.Th>Status</Table.Th><Table.Th>Action</Table.Th></Table.Tr></Table.Thead>
              <Table.Tbody>{requests.map((item) => <Table.Tr key={item.id}>
                <Table.Td>{item.category}</Table.Td>
                <Table.Td>{item.starts_on} – {item.ends_on}</Table.Td><Table.Td>{item.chargeable_days}</Table.Td>
                <Table.Td><Badge variant="light">{item.status.replaceAll("_", " ")}</Badge></Table.Td>
                <Table.Td>
                  {[
                    "awaiting_substitute", "applicant_action_required", "awaiting_unit_head",
                    "awaiting_establishment", "awaiting_final_sanction", "awaiting_director_self",
                  ].includes(item.status) && (
                    <Button size="xs" variant="light" color="red" onClick={async () => {
                      try { await requestAction(item.id, "withdraw"); await refresh(); }
                      catch (error) {
                        notifications.show({ color: "red", title: "Could not withdraw", message: errorMessage(error) });
                      }
                    }}>Withdraw</Button>
                  )}
                </Table.Td>
              </Table.Tr>)}</Table.Tbody>
            </Table></Table.ScrollContainer> : <Alert color="gray">No leave requests yet.</Alert>}
          </Card>
        </Grid.Col>
      </Grid>
    </Container>
  );
}
