import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Badge, Button, Card, Container, Group, Select, Stack, Table, Text, TextInput, Textarea, Title } from "@mantine/core";
import { DateInput } from "@mantine/dates";
import { notifications } from "@mantine/notifications";
import { http, errorMessage } from "../../../lib/http";

type LeaveRow = {
  id: number; category: string; start_date: string; end_date: string;
  reason: string; status: string; station_leave: boolean;
};
type BalanceRow = { id: number; year: number; category: string; entitled_days: string; used_days: string; available_days: string };
type Props = { view: "requests" | "balances" | "queue" };

export default function ELMPage({ view }: Props) {
  const qc = useQueryClient();
  const [category, setCategory] = useState<string | null>("CL");
  const [start, setStart] = useState<string | null>(null);
  const [end, setEnd] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const [station, setStation] = useState(false);
  const [destination, setDestination] = useState("");
  const [note, setNote] = useState("");
  const url = view === "balances" ? "/elm/balances" : view === "queue" ? "/elm/requests/queue" : "/elm/requests";
  const query = useQuery({
    queryKey: ["elm", view],
    queryFn: async () => (await http.get(url)).data,
  });
  const submit = useMutation({
    mutationFn: async () => {
      if (!category || !start || !end) throw new Error("Select category and dates");
      return http.post("/elm/requests", {
        category, start_date: start, end_date: end, reason,
        station_leave: station, station_destination: destination,
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["elm"] });
      setReason("");
      notifications.show({ title: "Request submitted", message: "Leave request saved." });
    },
    onError: (err) => notifications.show({ color: "red", title: "Could not submit", message: errorMessage(err) }),
  });
  const decide = useMutation({
    mutationFn: async ({ id, decision }: { id: number; decision: string }) =>
      http.post(`/elm/requests/${id}/decision`, { decision, note }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["elm"] }),
    onError: (err) => notifications.show({ color: "red", title: "Could not update request", message: errorMessage(err) }),
  });

  const title = view === "balances" ? "My Leave Balances" : view === "queue" ? "Leave Approval Queue" : "Employee Leave Management";
  const rows = query.data ?? [];
  return <Container size="xl" py="lg"><Stack>
    <Title order={2}>{title}</Title>
    {query.error && <Text c="red">{errorMessage(query.error)}</Text>}
    {view === "requests" && <Card withBorder><Stack>
      <Title order={4}>Apply for leave</Title>
      <Select label="Leave category" data={["CL", "RH", "SCL", "EL", "COL", "VL"]} value={category} onChange={setCategory} />
      <Group grow><DateInput label="Start date" value={start} onChange={setStart} /><DateInput label="End date" value={end} onChange={setEnd} /></Group>
      <Textarea label="Purpose / reason" value={reason} onChange={(e) => setReason(e.currentTarget.value)} />
      <Select label="Station Leave" data={[{ value: "no", label: "No" }, { value: "yes", label: "Yes" }]} value={station ? "yes" : "no"} onChange={(v) => setStation(v === "yes")} />
      {station && <TextInput label="Destination" value={destination} onChange={(e) => setDestination(e.currentTarget.value)} />}
      <Button loading={submit.isPending} onClick={() => submit.mutate()}>Submit request</Button>
    </Stack></Card>}
    {view === "queue" && <TextInput label="Decision note" value={note} onChange={(e) => setNote(e.currentTarget.value)} />}
    <Card withBorder><Table.ScrollContainer minWidth={600}><Table striped><Table.Thead><Table.Tr>
      {(view === "balances" ? ["Year", "Category", "Entitled", "Used", "Available"] : ["ID", "Category", "Period", "Reason", "Status", "Action"]).map((v) => <Table.Th key={v}>{v}</Table.Th>)}
    </Table.Tr></Table.Thead><Table.Tbody>
      {view === "balances" ? (rows as BalanceRow[]).map((r) => <Table.Tr key={r.id}><Table.Td>{r.year}</Table.Td><Table.Td>{r.category}</Table.Td><Table.Td>{r.entitled_days}</Table.Td><Table.Td>{r.used_days}</Table.Td><Table.Td>{r.available_days}</Table.Td></Table.Tr>) : (rows as LeaveRow[]).map((r) => <Table.Tr key={r.id}><Table.Td>{r.id}</Table.Td><Table.Td>{r.category}</Table.Td><Table.Td>{r.start_date} - {r.end_date}</Table.Td><Table.Td>{r.reason}</Table.Td><Table.Td><Badge>{r.status}</Badge></Table.Td><Table.Td>{view === "queue" && r.status === "pending" && <Group><Button size="xs" onClick={() => decide.mutate({ id: r.id, decision: "approve" })}>Approve</Button><Button size="xs" color="red" onClick={() => decide.mutate({ id: r.id, decision: "reject" })}>Reject</Button></Group>}</Table.Td></Table.Tr>)}
    </Table.Tbody></Table></Table.ScrollContainer>
      {rows.length === 0 && <Text c="dimmed" size="sm" p="md">No records yet.</Text>}
    </Card>
  </Stack></Container>;
}
