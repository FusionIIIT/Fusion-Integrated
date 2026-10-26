import { useState, type FormEvent } from "react";
import { Alert, Button, Card, Group, Select, Stack, Table, Text, TextInput, Textarea, Title } from "@mantine/core";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { http, errorMessage } from "../../lib/http";
import { useAuth } from "../../auth/AuthProvider";

type Leave = { id: number; employee_id: number; category: string; start_date: string; end_date: string; half_day: string; reason: string; status: string; current_stage: string; chargeable_days: string };
type Balance = { category: string; year: number; allotted: string; reserved: string; used: string; available: string };
type LeaveType = { code: string; label: string };
const key = ["elm"];

export default function LeavePage() {
  const { can } = useAuth();
  const selfService = can("leave_elm.application.apply");
  const mayReview = can("leave_elm.application.review");
  const qc = useQueryClient();
  const [form, setForm] = useState({ category: "CL", start_date: "", end_date: "", half_day: "", reason: "" });
  const [error, setError] = useState("");
  const types = useQuery({ queryKey: [...key, "types"], enabled: selfService, queryFn: async () => (await http.get<LeaveType[]>("/leave/types")).data });
  const mine = useQuery({ queryKey: [...key, "mine"], enabled: selfService, queryFn: async () => (await http.get<Leave[]>("/leave/applications")).data });
  const balances = useQuery({ queryKey: [...key, "balance"], enabled: can("leave_elm.balance.view"), queryFn: async () => (await http.get<Balance[]>("/leave/balance")).data });
  const pending = useQuery({ queryKey: [...key, "pending"], enabled: mayReview, queryFn: async () => (await http.get<Leave[]>("/leave/applications/pending")).data });
  const mutate = useMutation({ mutationFn: async ({ url, body }: { url: string; body: unknown }) => (await http.post(url, body)).data,
    onSuccess: () => { setError(""); qc.invalidateQueries({ queryKey: key }); }, onError: (e) => setError(errorMessage(e)) });
  const submit = (event: FormEvent) => { event.preventDefault(); mutate.mutate({ url: "/leave/applications", body: form }); };
  const decide = (a: Leave, approve: boolean) => {
    const higher = !["CL", "RH"].includes(a.category);
    const body = a.current_stage === "establishment" ? {} :
      a.current_stage === "unit_head" && higher ? { recommended: approve } : { approve };
    mutate.mutate({ url: `/leave/applications/${a.id}/decide`, body });
  };
  const withdraw = (id: number) => mutate.mutate({ url: `/leave/applications/${id}/withdraw`, body: {} });
  return <Stack p="md"><Title order={2}>Employee Leave</Title>{error && <Alert color="red">{error}</Alert>}
    {can("leave_elm.balance.view") && <Card withBorder><Title order={4}>Available balance</Title><Table><Table.Thead><Table.Tr><Table.Th>Category</Table.Th><Table.Th>Year</Table.Th><Table.Th>Available</Table.Th></Table.Tr></Table.Thead><Table.Tbody>{balances.data?.map((b) => <Table.Tr key={`${b.category}-${b.year}`}><Table.Td>{b.category}</Table.Td><Table.Td>{b.year}</Table.Td><Table.Td>{b.available}</Table.Td></Table.Tr>)}</Table.Tbody></Table></Card>}
    {selfService && <><Card withBorder><Title order={4}>Apply for leave</Title><form onSubmit={submit}><Group grow align="end"><Select label="Category" data={types.data?.map((t) => ({ value: t.code, label: t.label })) ?? []} value={form.category} onChange={(v) => setForm({ ...form, category: v ?? "CL" })} /><TextInput type="date" label="From" required value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.currentTarget.value })} /><TextInput type="date" label="To" required value={form.end_date} onChange={(e) => setForm({ ...form, end_date: e.currentTarget.value })} /><Select label="CL half day" data={[{ value: "", label: "Full day" }, { value: "first", label: "First half" }, { value: "second", label: "Second half" }]} value={form.half_day} onChange={(v) => setForm({ ...form, half_day: v ?? "" })} /></Group><Textarea mt="sm" label="Reason" required maxLength={2000} value={form.reason} onChange={(e) => setForm({ ...form, reason: e.currentTarget.value })} /><Button mt="sm" type="submit" loading={mutate.isPending}>Submit</Button></form></Card>
    <Card withBorder><Title order={4}>My applications</Title>{mine.data?.map((a) => <Group key={a.id} justify="space-between"><Text>{a.category}: {a.start_date} – {a.end_date} · {a.status} ({a.chargeable_days} days)</Text>{a.status === "pending" && <Button variant="light" onClick={() => withdraw(a.id)}>Withdraw</Button>}</Group>)}</Card></>}
    {mayReview && <Card withBorder><Title order={4}>Assigned review queue</Title>{pending.data?.map((a) => <Group key={a.id} justify="space-between"><Text>User {a.employee_id} · {a.category}: {a.start_date} – {a.end_date} · {a.current_stage}<br />{a.reason}</Text><Group>{a.current_stage === "establishment" ? <Button onClick={() => decide(a, true)}>Verify &amp; forward</Button> : <><Button onClick={() => decide(a, true)}>{a.current_stage === "unit_head" && !["CL", "RH"].includes(a.category) ? "Recommend" : "Approve"}</Button><Button color="red" onClick={() => decide(a, false)}>{a.current_stage === "unit_head" && !["CL", "RH"].includes(a.category) ? "Not recommend" : "Reject"}</Button></>}</Group></Group>)}</Card>}
  </Stack>;
}
