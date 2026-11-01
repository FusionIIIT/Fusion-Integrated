import { useState } from "react";
import { Button, Card, Container, Group, Select, Stack, Table, Text, TextInput, Title } from "@mantine/core";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage, http } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import type { Registration } from "../api/types";

interface Survey { readonly survey: { readonly id: number; readonly title: string; readonly vacation_start: string; readonly vacation_end: string; readonly response_deadline: string }; readonly responses: readonly { readonly response: string | null; readonly defaulted: boolean; readonly count: number }[] }
interface Feedback { readonly id: number; readonly text: string; readonly created_at: string }
interface Rebate { readonly id: number; readonly user_id: number; readonly reason: string; readonly start_date: string; readonly end_date: string; readonly status: string }
interface SpecialFood { readonly id: number; readonly user_id: number; readonly requested_date: string; readonly description: string; readonly status: string }

export default function OperationsPage() {
  const { can } = useAuth();
  const client = useQueryClient();
  const [cycle, setCycle] = useState("");
  const [opens, setOpens] = useState("");
  const [closes, setCloses] = useState("");
  const [surveyTitle, setSurveyTitle] = useState("");
  const [vacationStart, setVacationStart] = useState("");
  const [vacationEnd, setVacationEnd] = useState("");
  const [surveyDeadline, setSurveyDeadline] = useState("");
  const [weekStart, setWeekStart] = useState("");
  const [menuDay, setMenuDay] = useState<string | null>("0");
  const [menuMeal, setMenuMeal] = useState<string | null>("breakfast");
  const [menuItem, setMenuItem] = useState("");
  const [announcementTitle, setAnnouncementTitle] = useState("");
  const [announcementBody, setAnnouncementBody] = useState("");
  const registrations = useQuery({ queryKey: ["mms", "registrations"], queryFn: async () => (await http.get<Registration[]>("/mms/registrations/")).data });
  const surveys = useQuery({ queryKey: ["mms", "surveys"], queryFn: async () => (await http.get<Survey[]>("/mms/vacation-surveys/")).data, enabled: can("mms.vacation.manage") });
  const feedback = useQuery({ queryKey: ["mms", "feedback"], queryFn: async () => (await http.get<Feedback[]>("/mms/feedback/")).data, enabled: can("mms.feedback.view") });
  const rebates = useQuery({ queryKey: ["mms", "rebates"], queryFn: async () => (await http.get<Rebate[]>("/mms/rebates/")).data, enabled: can("mms.rebate.view") });
  const specialFood = useQuery({ queryKey: ["mms", "special-food"], queryFn: async () => (await http.get<SpecialFood[]>("/mms/special-food/")).data, enabled: can("mms.special_food.view") });
  const decide = useMutation({ mutationFn: async ({ id, decision }: { id: number; decision: "approve" | "reject" }) => http.post(`/mms/registrations/${id}/decision/`, { decision }), onSuccess: () => client.invalidateQueries({ queryKey: ["mms"] }) });
  const window = useMutation({ mutationFn: async () => http.post("/mms/registration-windows/", { cycle, opens_at: new Date(opens).toISOString(), closes_at: new Date(closes).toISOString() }), onSuccess: () => client.invalidateQueries({ queryKey: ["mms"] }) });
  const createSurvey = useMutation({ mutationFn: async () => http.post("/mms/vacation-surveys/", { title: surveyTitle, vacation_start: vacationStart, vacation_end: vacationEnd, response_deadline: new Date(surveyDeadline).toISOString() }), onSuccess: () => client.invalidateQueries({ queryKey: ["mms"] }) });
  const createMenuItem = useMutation({ mutationFn: async () => http.post("/mms/menu/", { week_start: weekStart, day: Number(menuDay), meal: menuMeal, item: menuItem }), onSuccess: () => { setMenuItem(""); client.invalidateQueries({ queryKey: ["mms"] }); } });
  const createAnnouncement = useMutation({ mutationFn: async () => http.post("/mms/announcements/", { title: announcementTitle, body: announcementBody }), onSuccess: () => { setAnnouncementTitle(""); setAnnouncementBody(""); client.invalidateQueries({ queryKey: ["mms"] }); } });
  const decideRebate = useMutation({ mutationFn: async ({ id, decision }: { id: number; decision: "approve" | "reject" }) => http.post(`/mms/rebates/${id}/decision/`, { decision }), onSuccess: () => client.invalidateQueries({ queryKey: ["mms"] }) });
  const decideSpecial = useMutation({ mutationFn: async ({ id, decision }: { id: number; decision: "approve" | "reject" }) => http.post(`/mms/special-food/${id}/decision/`, { decision }), onSuccess: () => client.invalidateQueries({ queryKey: ["mms"] }) });
  const fulfillSpecial = useMutation({ mutationFn: async ({ id, outcome }: { id: number; outcome: "served" | "cancelled" }) => http.post(`/mms/special-food/${id}/fulfillment/`, { status: outcome }), onSuccess: () => client.invalidateQueries({ queryKey: ["mms"] }) });
  const error = registrations.error ?? surveys.error ?? feedback.error ?? rebates.error ?? specialFood.error;
  if (error) return <Container size="lg"><ErrorState error={error} /></Container>;
  return <Container size="lg"><PageHeader title="Mess Operations" subtitle="Requests, surveys, and feedback" />
    {can("mms.registration.decide") && <Card withBorder mb="md"><Stack><Title order={4}>Open a registration window</Title>
      <Group align="end"><TextInput label="Mess cycle" value={cycle} onChange={(event) => setCycle(event.currentTarget.value)} />
        <TextInput type="datetime-local" label="Opens" value={opens} onChange={(event) => setOpens(event.currentTarget.value)} />
        <TextInput type="datetime-local" label="Closes" value={closes} onChange={(event) => setCloses(event.currentTarget.value)} />
        <Button disabled={!cycle || !opens || !closes || window.isPending} onClick={() => window.mutate()}>Open window</Button></Group>
      {window.error && <Text c="red">{errorMessage(window.error)}</Text>}</Stack></Card>}
    {can("mms.registration.view") && <Card withBorder mb="md"><Title order={4} mb="sm">Registration requests</Title>
      <Table><Table.Thead><Table.Tr><Table.Th>Cycle</Table.Th><Table.Th>Request</Table.Th><Table.Th>Status</Table.Th><Table.Th>Submitted</Table.Th><Table.Th>Decision</Table.Th></Table.Tr></Table.Thead>
        <Table.Tbody>{registrations.data?.map((row) => <Table.Tr key={row.id}><Table.Td>{row.cycle}</Table.Td><Table.Td>{row.request_type}</Table.Td><Table.Td>{row.status}</Table.Td><Table.Td>{new Date(row.submitted_at).toLocaleString()}</Table.Td><Table.Td>
          {row.status === "pending" && can("mms.registration.decide") ? <Group gap="xs"><Button size="xs" onClick={() => decide.mutate({ id: row.id, decision: "approve" })}>Approve</Button><Button size="xs" color="red" variant="light" onClick={() => decide.mutate({ id: row.id, decision: "reject" })}>Reject</Button></Group> : row.effective_date ?? "—"}
        </Table.Td></Table.Tr>)}</Table.Tbody></Table>{decide.error && <Text c="red">{errorMessage(decide.error)}</Text>}
    </Card>}
    {can("mms.vacation.manage") && <Card withBorder mb="md"><Title order={4} mb="sm">Vacation surveys</Title>
      <Group align="end" mb="sm"><TextInput label="Survey" value={surveyTitle} onChange={(event) => setSurveyTitle(event.currentTarget.value)} />
        <TextInput type="date" label="Vacation starts" value={vacationStart} onChange={(event) => setVacationStart(event.currentTarget.value)} />
        <TextInput type="date" label="Vacation ends" value={vacationEnd} onChange={(event) => setVacationEnd(event.currentTarget.value)} />
        <TextInput type="datetime-local" label="Response deadline" value={surveyDeadline} onChange={(event) => setSurveyDeadline(event.currentTarget.value)} />
        <Button disabled={!surveyTitle || !vacationStart || !vacationEnd || !surveyDeadline || createSurvey.isPending} onClick={() => createSurvey.mutate()}>Create survey</Button></Group>
      {createSurvey.error && <Text c="red">{errorMessage(createSurvey.error)}</Text>}
      {surveys.data?.map((record) => <Text key={record.survey.id}>{record.survey.title}: {record.survey.vacation_start} to {record.survey.vacation_end}, replies due {new Date(record.survey.response_deadline).toLocaleString()}</Text>)}
      {(surveys.data?.length ?? 0) === 0 && <Text c="dimmed">No surveys created.</Text>}
    </Card>}
    {can("mms.menu.manage") && <Card withBorder mb="md"><Title order={4} mb="sm">Add a weekly menu item</Title>
      <Group align="end"><TextInput type="date" label="Week starts" value={weekStart} onChange={(event) => setWeekStart(event.currentTarget.value)} />
        <Select label="Day" value={menuDay} onChange={setMenuDay} data={["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"].map((label, index) => ({ value: String(index), label }))} />
        <Select label="Meal" value={menuMeal} onChange={setMenuMeal} data={["breakfast", "lunch", "dinner"]} />
        <TextInput label="Menu item" value={menuItem} onChange={(event) => setMenuItem(event.currentTarget.value)} />
        <Button disabled={!weekStart || !menuDay || !menuMeal || !menuItem || createMenuItem.isPending} onClick={() => createMenuItem.mutate()}>Add item</Button></Group>
      {createMenuItem.error && <Text c="red">{errorMessage(createMenuItem.error)}</Text>}
    </Card>}
    {can("mms.rebate.decide") && <Card withBorder mb="md"><Title order={4} mb="sm">Rebate decisions</Title>
      {rebates.data?.filter((row) => row.status === "pending").map((row) => <Group key={row.id} justify="space-between" mb="xs"><Text>Student {row.user_id} · {row.start_date} to {row.end_date} · {row.reason}</Text>
        <Group gap="xs"><Button size="xs" onClick={() => decideRebate.mutate({ id: row.id, decision: "approve" })}>Approve</Button><Button size="xs" color="red" variant="light" onClick={() => decideRebate.mutate({ id: row.id, decision: "reject" })}>Reject</Button></Group></Group>)}
      {decideRebate.error && <Text c="red">{errorMessage(decideRebate.error)}</Text>}
    </Card>}
    {can("mms.special_food.view") && <Card withBorder mb="md"><Title order={4} mb="sm">Special food requests</Title>
      {specialFood.data?.map((row) => <Group key={row.id} justify="space-between" mb="xs"><Text>Student {row.user_id} · {row.requested_date} · {row.description} · {row.status}</Text>
        {row.status === "requested" && can("mms.special_food.decide") && <Group gap="xs"><Button size="xs" onClick={() => decideSpecial.mutate({ id: row.id, decision: "approve" })}>Approve</Button><Button size="xs" color="red" variant="light" onClick={() => decideSpecial.mutate({ id: row.id, decision: "reject" })}>Reject</Button></Group>}
        {row.status === "approved" && can("mms.special_food.decide") && <Group gap="xs"><Button size="xs" onClick={() => fulfillSpecial.mutate({ id: row.id, outcome: "served" })}>Served</Button><Button size="xs" variant="light" onClick={() => fulfillSpecial.mutate({ id: row.id, outcome: "cancelled" })}>Cancelled</Button></Group>}</Group>)}
      {decideSpecial.error && <Text c="red">{errorMessage(decideSpecial.error)}</Text>}{fulfillSpecial.error && <Text c="red">{errorMessage(fulfillSpecial.error)}</Text>}
    </Card>}
    {can("mms.announcement.publish") && <Card withBorder mb="md"><Stack><Title order={4}>Publish an announcement</Title>
      <TextInput label="Title" value={announcementTitle} onChange={(event) => setAnnouncementTitle(event.currentTarget.value)} />
      <TextInput label="Announcement" value={announcementBody} onChange={(event) => setAnnouncementBody(event.currentTarget.value)} />
      <Button disabled={!announcementTitle || !announcementBody || createAnnouncement.isPending} onClick={() => createAnnouncement.mutate()}>Publish</Button>
      {createAnnouncement.error && <Text c="red">{errorMessage(createAnnouncement.error)}</Text>}</Stack>
    </Card>}
    {can("mms.feedback.view") && <Card withBorder><Title order={4} mb="sm">Student feedback</Title>
      {feedback.data?.map((entry) => <Text key={entry.id} mb="xs">{entry.text}</Text>)}
      {(feedback.data?.length ?? 0) === 0 && <Text c="dimmed">No feedback has been submitted.</Text>}
    </Card>}
  </Container>;
}
