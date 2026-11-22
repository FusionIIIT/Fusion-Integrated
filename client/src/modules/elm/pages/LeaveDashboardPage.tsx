import { useState } from "react";
import { Button, Card, Container, Group, SimpleGrid, Stack, Table, Text, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCreateLeaveApplication, useLeaveApplications, useLeaveBalances, useWithdrawLeave } from "../api/hooks";

export default function LeaveDashboardPage() {
  const balances = useLeaveBalances();
  const applications = useLeaveApplications();
  const create = useCreateLeaveApplication();
  const withdraw = useWithdrawLeave();
  const [category, setCategory] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [reason, setReason] = useState("");
  function submit() {
    create.mutate({ category_code: category, start_date: start, end_date: end, reason }, {
      onSuccess: () => { notifications.show({ color: "green", message: "Leave application submitted" }); setReason(""); },
      onError: () => notifications.show({ color: "red", message: "Leave application could not be submitted" }),
    });
  }
  const rows = applications.data?.results ?? [];
  return <Container size="lg"><PageHeader title="Employee Leave" subtitle="Balances and leave applications" />
    <SimpleGrid cols={{ base: 1, sm: 3 }} mb="lg">{(balances.data?.results ?? []).map((item) => <Card withBorder key={item.id}><Text fw={600}>{item.category.label}</Text><Text size="xl" fw={700}>{item.available}</Text><Text size="xs" c="dimmed">available days</Text></Card>)}</SimpleGrid>
    <Card withBorder mb="lg"><Stack><Text fw={600}>New application</Text><Group grow><TextInput label="Category code" placeholder="CL" value={category} onChange={(e) => setCategory(e.currentTarget.value)} /><TextInput label="Start date" type="date" value={start} onChange={(e) => setStart(e.currentTarget.value)} /><TextInput label="End date" type="date" value={end} onChange={(e) => setEnd(e.currentTarget.value)} /></Group><TextInput label="Reason" value={reason} onChange={(e) => setReason(e.currentTarget.value)} /><Button onClick={submit} loading={create.isPending} disabled={!category || !start || !end}>Submit leave application</Button></Stack></Card>
    <Card withBorder><Text fw={600} mb="sm">Applications</Text><Table striped><Table.Thead><Table.Tr><Table.Th>Category</Table.Th><Table.Th>Dates</Table.Th><Table.Th>Status</Table.Th><Table.Th /></Table.Tr></Table.Thead><Table.Tbody>{rows.map((item) => <Table.Tr key={item.id}><Table.Td>{item.category.label}</Table.Td><Table.Td>{item.start_date} to {item.end_date}</Table.Td><Table.Td>{item.status}</Table.Td><Table.Td>{item.status === "pending" && <Button size="xs" color="red" variant="subtle" loading={withdraw.isPending} onClick={() => withdraw.mutate(item.id)}>Withdraw</Button>}</Table.Td></Table.Tr>)}</Table.Tbody></Table></Card></Container>;
}
