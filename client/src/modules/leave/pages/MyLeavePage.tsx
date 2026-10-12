import { useState } from "react";
import { Alert, Button, Card, Checkbox, Container, Grid, Group, Select, Stack, Table, Text, TextInput, Textarea } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useApplyForLeave, useEmployeeSearch, useMyLeave, useWithdrawLeave } from "../api";

export default function MyLeavePage() {
  const { categories, requests, balances } = useMyLeave();
  const apply = useApplyForLeave();
  const withdraw = useWithdrawLeave();
  const [category, setCategory] = useState<string | null>(null);
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [reason, setReason] = useState("");
  const [portion, setPortion] = useState("full");
  const [stationLeave, setStationLeave] = useState(false);
  const [destination, setDestination] = useState("");
  const [departure, setDeparture] = useState("");
  const [returnTime, setReturnTime] = useState("");
  const [substituteSearch, setSubstituteSearch] = useState("");
  const [substituteUserId, setSubstituteUserId] = useState<string | null>(null);
  const employees = useEmployeeSearch(substituteSearch);
  if (requests.error) return <Container size="lg"><ErrorState error={requests.error} /></Container>;

  function submit() {
    if (!category || !start || !end || !reason.trim()) return;
    apply.mutate({ category_code: category, start_date: start, end_date: end,
      reason, cl_portion: category === "CL" ? portion : "full", station_leave: stationLeave,
      station_destination: destination,
      station_departure_at: departure ? new Date(departure).toISOString() : null,
      station_return_at: returnTime ? new Date(returnTime).toISOString() : null,
      substitute_user_id: substituteUserId ? Number(substituteUserId) : null }, {
      onSuccess: () => { setReason(""); setStationLeave(false); setDestination(""); setDeparture(""); setReturnTime(""); setSubstituteUserId(null); notifications.show({ color: "green", title: "Leave request submitted", message: "You can follow its progress in your request history." }); },
      onError: (error) => notifications.show({ color: "red", title: "Could not submit request", message: errorMessage(error) }),
    });
  }

  return <Container size="lg">
    <PageHeader title="My Leave" subtitle="Apply for leave and review your balances and requests." />
    <Grid gutter="md" mb="lg">
      {(balances.data?.results ?? []).map((balance) => <Grid.Col key={balance.id} span={{ base: 12, sm: 6, md: 4 }}>
        <Card withBorder h="100"><Text fw={600}>{balance.category_code} · {balance.year}</Text>
          <Text size="sm" c="dimmed">Available</Text><Text size="xl" fw={700}>{balance.available} days</Text>
          <Text size="xs" c="dimmed">Entitlement {balance.entitlement}; carried forward {balance.carried_over}</Text>
        </Card>
      </Grid.Col>)}
    </Grid>
    <Card withBorder mb="lg">
      <Text fw={600} mb="md">New leave application</Text>
      <Stack gap="sm">
        <Select label="Leave category" placeholder="Select a category" value={category}
          onChange={setCategory} data={(categories.data?.results ?? []).map((item) => ({ value: item.code, label: `${item.code} · ${item.label}` }))} />
        <Group grow>
          <TextInput type="date" label="From" value={start} onChange={(e) => setStart(e.currentTarget.value)} />
          <TextInput type="date" label="Through" value={end} onChange={(e) => setEnd(e.currentTarget.value)} />
        </Group>
        {category === "CL" && <Select label="CL portion" value={portion} onChange={(v) => setPortion(v ?? "full")}
          data={[{ value: "full", label: "Full day" }, { value: "first_half", label: "First half" }, { value: "second_half", label: "Second half" }]} />}
        {(category === "CL" || category === "RH") && <Checkbox label="I will be outside Jabalpur (Station Leave)" checked={stationLeave} onChange={(e) => setStationLeave(e.currentTarget.checked)} />}
        {stationLeave && <>
          <TextInput label="Destination" value={destination} onChange={(e) => setDestination(e.currentTarget.value)} />
          <Group grow><TextInput type="datetime-local" label="Departure" value={departure} onChange={(e) => setDeparture(e.currentTarget.value)} />
            <TextInput type="datetime-local" label="Return" value={returnTime} onChange={(e) => setReturnTime(e.currentTarget.value)} /></Group>
        </>}
        <Select label="Substitute (when responsibility coverage is required)" placeholder="Search employees"
          searchable clearable searchValue={substituteSearch} onSearchChange={setSubstituteSearch}
          value={substituteUserId} onChange={setSubstituteUserId} nothingFoundMessage={substituteSearch.length < 2 ? "Type at least two characters" : "No eligible employee found"}
          data={(employees.data ?? []).map((person) => ({ value: String(person.user_id), label: `${person.label} · ${person.kind}` }))} />
        <Textarea label="Purpose / reason" value={reason} onChange={(e) => setReason(e.currentTarget.value)} minRows={2} />
        <Button onClick={submit} loading={apply.isPending} disabled={!category || !start || !end || !reason.trim() || (stationLeave && (!destination || !departure || !returnTime))}>Submit application</Button>
      </Stack>
    </Card>
    <Card withBorder>
      <Text fw={600} mb="sm">Request history</Text>
      {(requests.data?.results?.length ?? 0) === 0 ? <Alert color="gray">No leave applications yet.</Alert> :
        <Table.ScrollContainer minWidth={640}><Table striped highlightOnHover>
          <Table.Thead><Table.Tr><Table.Th>Category</Table.Th><Table.Th>Period</Table.Th><Table.Th>Days</Table.Th><Table.Th>Status</Table.Th><Table.Th /></Table.Tr></Table.Thead>
          <Table.Tbody>{requests.data?.results.map((item) => <Table.Tr key={item.id}>
            <Table.Td>{item.category_code}</Table.Td><Table.Td>{item.start_date} – {item.end_date}</Table.Td>
            <Table.Td>{item.duration_days}</Table.Td><Table.Td>{item.status.replaceAll("_", " ")}</Table.Td>
            <Table.Td>{["awaiting_substitute", "applicant_action", "pending_unit_head", "pending_establishment", "pending_authority"].includes(item.status) &&
              <Button size="xs" variant="light" color="red" loading={withdraw.isPending} onClick={() => withdraw.mutate(item.id, {
                onError: (error) => notifications.show({ color: "red", title: "Could not withdraw request", message: errorMessage(error) }),
              })}>Withdraw</Button>}</Table.Td>
          </Table.Tr>)}</Table.Tbody>
        </Table></Table.ScrollContainer>}
    </Card>
  </Container>;
}
