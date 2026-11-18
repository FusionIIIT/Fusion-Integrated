import { Fragment, useState } from "react";
import { Badge, Button, Card, Checkbox, Container, Group, Select, Stack, Table, Text, TextInput, Textarea, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { errorMessage } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { ErrorState } from "../../../ui/components/ErrorState";
import { useCreateLeave, useLeaveAction, useMyLeave, useReplacementSubstitute, useSubstituteResponse, useSubstitutions } from "../api";

const categories = ["CL", "RH", "SCL", "EL", "COL", "VL"].map((value) => ({ value, label: value }));
export default function MyLeavePage() {
  const query = useMyLeave(); const substitutions = useSubstitutions(); const respond = useSubstituteResponse(); const replacement = useReplacementSubstitute(); const create = useCreateLeave(); const action = useLeaveAction();
  const [category, setCategory] = useState<string | null>("CL");
  const [start, setStart] = useState(""); const [end, setEnd] = useState("");
  const [half, setHalf] = useState<string | null>(""); const [purpose, setPurpose] = useState("");
  const [substitute, setSubstitute] = useState(""); const [station, setStation] = useState(false); const [expandedId, setExpandedId] = useState<number | null>(null); const [stationFrom, setStationFrom] = useState(""); const [stationTo, setStationTo] = useState(""); const [stationAddress, setStationAddress] = useState("");
  if (query.error) return <Container size="lg"><ErrorState error={query.error} /></Container>;
  function submit() {
    create.mutate({ category, start_date: start, end_date: end, half: category === "CL" ? (half ?? "") : "", purpose,
      substitute_user_id: substitute ? Number(substitute) : null, station_leave: station, station_leave_from: station ? stationFrom || null : null, station_leave_to: station ? stationTo || null : null, station_leave_address: station ? stationAddress : "" }, {
      onSuccess: () => { notifications.show({ color: "green", title: "Request submitted", message: "Your leave request was submitted." }); setPurpose(""); setSubstitute(""); },
      onError: (e) => notifications.show({ color: "red", title: "Could not submit leave", message: errorMessage(e) }),
    });
  }
  function runAction(id: number, type: "withdraw" | "cancel") {
    const payload = type === "cancel" ? { reason: "Requested by employee" } : {};
    action.mutate({ id, action: type, payload }, { onSuccess: () => notifications.show({ color: "green", title: "Request updated", message: `Request #${id} updated.` }), onError: (e) => notifications.show({ color: "red", title: "Action failed", message: errorMessage(e) }) });
  }
  function runExtension(id: number) {
    const endDate = window.prompt("New extension end date (YYYY-MM-DD)");
    if (!endDate) return;
    action.mutate({ id, action: "extend", payload: { end_date: endDate } }, { onSuccess: () => notifications.show({ color: "green", title: "Extension submitted", message: `Extension for request #${id} is awaiting review.` }), onError: (e) => notifications.show({ color: "red", title: "Extension failed", message: errorMessage(e) }) });
  }
  function runResumption(id: number) {
    const actualReturnDate = window.prompt("Actual resumption date (YYYY-MM-DD)");
    if (!actualReturnDate) return;
    action.mutate({ id, action: "resume", payload: { actual_return_date: actualReturnDate } }, { onSuccess: () => notifications.show({ color: "green", title: "Resumption submitted", message: `Resumption for request #${id} is awaiting review.` }), onError: (e) => notifications.show({ color: "red", title: "Resumption failed", message: errorMessage(e) }) });
  }
  function runReplacement(id: number) {
    const substituteId = window.prompt("Replacement substitute employee ID");
    if (!substituteId || !Number.isInteger(Number(substituteId))) return;
    replacement.mutate({ id, substitute_user_id: Number(substituteId) }, { onSuccess: () => notifications.show({ color: "green", title: "Replacement nominated", message: `Request #${id} is awaiting substitute response.` }), onError: (e) => notifications.show({ color: "red", title: "Replacement failed", message: errorMessage(e) }) });
  }
  return <Container size="lg">
    <PageHeader title="My Leave" subtitle="Apply for leave, track requests, and manage approved leave." />
    <Card withBorder mb="lg" padding="lg"><Stack>
      <Title order={3}>New leave application</Title>
      <Group grow align="flex-start"><Select label="Leave category" data={categories} value={category} onChange={setCategory} required />
        <TextInput type="date" label="Start date" value={start} onChange={(e) => setStart(e.currentTarget.value)} required />
        <TextInput type="date" label="End date" value={end} onChange={(e) => setEnd(e.currentTarget.value)} required /></Group>
      {category === "CL" && <Select label="CL day portion (optional)" data={[{ value: "first", label: "First half" }, { value: "second", label: "Second half" }]} clearable value={half} onChange={setHalf} />}
      <Textarea label="Purpose / reason" value={purpose} onChange={(e) => setPurpose(e.currentTarget.value)} />
      <TextInput label="Substitute employee ID (if applicable)" value={substitute} onChange={(e) => setSubstitute(e.currentTarget.value)} inputMode="numeric" />
      <Checkbox label="I will be outside Jabalpur during this leave (Station Leave)" checked={station} onChange={(e) => setStation(e.currentTarget.checked)} />
      {station && <><Group grow><TextInput label="Station leave from" type="date" value={stationFrom} onChange={(e) => setStationFrom(e.currentTarget.value)} /><TextInput label="Station leave to" type="date" value={stationTo} onChange={(e) => setStationTo(e.currentTarget.value)} /></Group><TextInput label="Address / destination" value={stationAddress} onChange={(e) => setStationAddress(e.currentTarget.value)} /></>}
      <Group justify="flex-end"><Button loading={create.isPending} disabled={!category || !start || !end} onClick={submit}>Submit leave request</Button></Group>
    </Stack></Card>
    {(substitutions.data ?? []).length > 0 && <><Title order={3} mb="sm">Substitute requests assigned to you</Title><Stack mb="lg">{(substitutions.data ?? []).map((row) => <Card withBorder key={row.id}><Group justify="space-between"><Stack gap={2}><Text fw={600}>Request #{row.id} · {row.category}</Text><Text size="sm">{row.start_date} – {row.end_date} · Employee ID {row.user_id}</Text></Stack><Group><Button size="xs" color="red" variant="light" onClick={() => respond.mutate({ id: row.id, accept: false })}>Decline</Button><Button size="xs" onClick={() => respond.mutate({ id: row.id, accept: true })}>Accept</Button></Group></Group></Card>)}</Stack></>}
    <Title order={3} mb="sm">Your requests</Title>
    {query.isPending ? <Text c="dimmed">Loading requests…</Text> : (query.data ?? []).length === 0 ? <Card withBorder><Text c="dimmed">No leave requests yet.</Text></Card> :
      <Table.ScrollContainer minWidth={760}><Table striped highlightOnHover><Table.Thead><Table.Tr><Table.Th>ID</Table.Th><Table.Th>Category</Table.Th><Table.Th>Dates</Table.Th><Table.Th>Days</Table.Th><Table.Th>Status</Table.Th><Table.Th>Action</Table.Th></Table.Tr></Table.Thead><Table.Tbody>
        {(query.data ?? []).map((row) => (
          <Fragment key={row.id}>
            <Table.Tr>
              <Table.Td>#{row.id}</Table.Td>
              <Table.Td>{row.category}</Table.Td>
              <Table.Td>{row.start_date} – {row.end_date}</Table.Td>
              <Table.Td>{row.days}</Table.Td>
              <Table.Td><Badge variant="light">{row.status.replaceAll("_", " ")}</Badge></Table.Td>
              <Table.Td>
                <Group gap="xs">
                  {["awaiting_substitute", "substitute_declined", "awaiting_unit_head", "awaiting_establishment", "awaiting_sanction", "awaiting_director"].includes(row.status) && <Button size="xs" variant="light" color="red" onClick={() => runAction(row.id, "withdraw")}>Withdraw</Button>}
                  {row.status === "substitute_declined" && <Button size="xs" variant="light" onClick={() => runReplacement(row.id)}>Replace substitute</Button>}
                  {row.status === "approved" && <Button size="xs" variant="light" color="orange" onClick={() => runAction(row.id, "cancel")}>Request cancellation</Button>}
                  <Button size="xs" variant="subtle" onClick={() => setExpandedId(expandedId === row.id ? null : row.id)}>History</Button>
                  <Button size="xs" variant="subtle" component="a" href={`/api/v1/elm/requests/${row.id}/print?format=csv`} target="_blank" rel="noreferrer">Export CSV</Button>
                  {row.status === "approved" && ["EL", "COL", "VL"].includes(row.category) && <><Button size="xs" variant="light" onClick={() => runExtension(row.id)}>Extend</Button><Button size="xs" variant="light" onClick={() => runResumption(row.id)}>Resumption</Button></>}
                </Group>
              </Table.Td>
            </Table.Tr>
            {expandedId === row.id && <Table.Tr><Table.Td colSpan={6}>
              <Stack gap="xs">
                {(row.history ?? []).length === 0 ? <Text c="dimmed" size="sm">No workflow history is recorded yet.</Text> : (row.history ?? []).map((entry, index) => (
                  <Group key={`${entry.at}-${index}`} justify="space-between" align="flex-start">
                    <Stack gap={1}>
                      <Text size="sm" fw={600}>{entry.event.replaceAll("_", " ")}: {entry.from || "new"} → {entry.to}</Text>
                      {entry.note && <Text size="xs" c="dimmed">{entry.note}</Text>}
                    </Stack>
                    <Text size="xs" c="dimmed">{new Date(entry.at).toLocaleString()}</Text>
                  </Group>
                ))}
              </Stack>
            </Table.Td></Table.Tr>}
          </Fragment>
        ))}
      </Table.Tbody></Table></Table.ScrollContainer>}
  </Container>;
}
