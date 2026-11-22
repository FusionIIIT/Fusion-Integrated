import { useState } from "react";
import { Button, Card, Container, Group, Select, Stack, Table, Text, TextInput, Title } from "@mantine/core";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage, http } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import type { MenuItem, Rebate, Registration } from "../api/types";

interface SpecialFood { readonly id: number; readonly requested_date: string; readonly description: string; readonly status: string }
interface StudentSurvey { readonly survey: { readonly id: number; readonly title: string; readonly vacation_start: string; readonly vacation_end: string; readonly response_deadline: string }; readonly response: string | null; readonly defaulted: boolean }
interface Announcement { readonly id: number; readonly title: string; readonly body: string; readonly created_at: string }
interface Feedback { readonly id: number; readonly text: string; readonly created_at: string }

const weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

export default function MyMessPage() {
  const { can } = useAuth();
  const client = useQueryClient();
  const [cycle, setCycle] = useState("");
  const [kind, setKind] = useState<string | null>("register");
  const [reason, setReason] = useState<string | null>("medical");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [explanation, setExplanation] = useState("");
  const [specialDate, setSpecialDate] = useState("");
  const [specialDescription, setSpecialDescription] = useState("");
  const [feedbackText, setFeedbackText] = useState("");
  const registrations = useQuery({ queryKey: ["mms", "registrations"], queryFn: async () =>
    (await http.get<Registration[]>("/mms/registrations/")).data, enabled: can("mms.registration.self") || can("mms.registration.view") });
  const menu = useQuery({ queryKey: ["mms", "menu"], queryFn: async () =>
    (await http.get<MenuItem[]>("/mms/menu/")).data, enabled: can("mms.menu.view") });
  const rebates = useQuery({ queryKey: ["mms", "rebates"], queryFn: async () =>
    (await http.get<Rebate[]>("/mms/rebates/")).data, enabled: can("mms.rebate.self") || can("mms.rebate.view") });
  const specialFood = useQuery({ queryKey: ["mms", "special-food"], queryFn: async () =>
    (await http.get<SpecialFood[]>("/mms/special-food/")).data, enabled: can("mms.special_food.self") });
  const surveys = useQuery({ queryKey: ["mms", "vacation-surveys"], queryFn: async () =>
    (await http.get<StudentSurvey[]>("/mms/vacation-surveys/")).data, enabled: can("mms.vacation.self") });
  const announcements = useQuery({ queryKey: ["mms", "announcements"], queryFn: async () =>
    (await http.get<Announcement[]>("/mms/announcements/")).data, enabled: can("mms.announcement.view") });
  const feedback = useQuery({ queryKey: ["mms", "feedback"], queryFn: async () =>
    (await http.get<Feedback[]>("/mms/feedback/")).data, enabled: can("mms.feedback.self") });
  const request = useMutation({ mutationFn: async () => http.post("/mms/registrations/", { cycle, request_type: kind }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["mms"] }) });
  const rebate = useMutation({ mutationFn: async () => http.post("/mms/rebates/", {
    reason, start_date: start, end_date: end, explanation,
  }), onSuccess: () => client.invalidateQueries({ queryKey: ["mms"] }) });
  const specialRequest = useMutation({ mutationFn: async () => http.post("/mms/special-food/", {
    requested_date: specialDate, description: specialDescription,
  }), onSuccess: () => client.invalidateQueries({ queryKey: ["mms"] }) });
  const respond = useMutation({ mutationFn: async ({ surveyId, response }: { surveyId: number; response: "yes" | "no" }) => http.post(`/mms/vacation-surveys/${surveyId}/response/`, { response }), onSuccess: () => client.invalidateQueries({ queryKey: ["mms", "vacation-surveys"] }) });
  const submitFeedback = useMutation({ mutationFn: async () => http.post("/mms/feedback/", { text: feedbackText }), onSuccess: () => { setFeedbackText(""); client.invalidateQueries({ queryKey: ["mms", "feedback"] }); } });
  const error = registrations.error ?? menu.error ?? rebates.error ?? specialFood.error ?? surveys.error ?? announcements.error ?? feedback.error;
  if (error) return <Container size="lg"><ErrorState error={error} /></Container>;

  return <Container size="lg">
    <PageHeader title="Mess Management" subtitle="Your requests and the current weekly menu" />
    {can("mms.registration.self") && <Card withBorder mb="md"><Stack>
      <Title order={4}>Registration</Title>
      <Group align="end"><TextInput label="Mess cycle" value={cycle} onChange={(event) => setCycle(event.currentTarget.value)} />
        <Select label="Request" value={kind} onChange={setKind} data={[{ value: "register", label: "Register" }, { value: "deregister", label: "Deregister" }]} />
        <Button disabled={!cycle || !kind || request.isPending} onClick={() => request.mutate()}>{request.isPending ? "Submitting" : "Submit request"}</Button>
      </Group>
      {request.error && <Text c="red">{errorMessage(request.error)}</Text>}
    </Stack></Card>}
    {can("mms.rebate.self") && <Card withBorder mb="md"><Stack>
      <Title order={4}>Request a rebate</Title>
      <Group align="end"><Select label="Reason" value={reason} onChange={setReason} data={[
        { value: "medical", label: "Medical" }, { value: "institute_leave", label: "Institute leave" },
        { value: "family_function", label: "Family function" }, { value: "other", label: "Other" },
      ]} /><TextInput type="date" label="Start date" value={start} onChange={(event) => setStart(event.currentTarget.value)} />
        <TextInput type="date" label="End date" value={end} onChange={(event) => setEnd(event.currentTarget.value)} />
        {reason === "other" && <TextInput label="Explanation" value={explanation} onChange={(event) => setExplanation(event.currentTarget.value)} />}
        <Button disabled={!reason || !start || !end || rebate.isPending} onClick={() => rebate.mutate()}>Submit rebate</Button>
      </Group>{rebate.error && <Text c="red">{errorMessage(rebate.error)}</Text>}
    </Stack></Card>}
    {(registrations.data?.length ?? 0) > 0 && <Card withBorder mb="md"><Title order={4} mb="sm">Registration history</Title>
      <Table><Table.Thead><Table.Tr><Table.Th>Cycle</Table.Th><Table.Th>Request</Table.Th><Table.Th>Status</Table.Th><Table.Th>Effective</Table.Th></Table.Tr></Table.Thead>
        <Table.Tbody>{registrations.data?.map((row) => <Table.Tr key={row.id}><Table.Td>{row.cycle}</Table.Td><Table.Td>{row.request_type}</Table.Td><Table.Td>{row.status}</Table.Td><Table.Td>{row.effective_date ?? "—"}</Table.Td></Table.Tr>)}</Table.Tbody></Table>
    </Card>}
    {(rebates.data?.length ?? 0) > 0 && <Card withBorder mb="md"><Title order={4} mb="sm">Rebate history</Title>
      <Table><Table.Thead><Table.Tr><Table.Th>Dates</Table.Th><Table.Th>Reason</Table.Th><Table.Th>Status</Table.Th></Table.Tr></Table.Thead>
        <Table.Tbody>{rebates.data?.map((row) => <Table.Tr key={row.id}><Table.Td>{row.start_date} to {row.end_date}</Table.Td><Table.Td>{row.reason}</Table.Td><Table.Td>{row.status}</Table.Td></Table.Tr>)}</Table.Tbody></Table>
    </Card>}
    {can("mms.special_food.self") && <Card withBorder mb="md"><Stack><Title order={4}>Special food request</Title>
      <Group align="end"><TextInput type="date" label="Requested date" value={specialDate} onChange={(event) => setSpecialDate(event.currentTarget.value)} />
        <TextInput label="Food request" value={specialDescription} onChange={(event) => setSpecialDescription(event.currentTarget.value)} />
        <Button disabled={!specialDate || !specialDescription || specialRequest.isPending} onClick={() => specialRequest.mutate()}>Submit request</Button></Group>
      {specialRequest.error && <Text c="red">{errorMessage(specialRequest.error)}</Text>}
      {specialFood.data?.map((item) => <Text key={item.id}>{item.requested_date} · {item.description} · {item.status}</Text>)}
    </Stack></Card>}
    {can("mms.vacation.self") && <Card withBorder mb="md"><Title order={4} mb="sm">Vacation food surveys</Title>
      {surveys.data?.map((item) => <Group key={item.survey.id} justify="space-between" mb="xs"><Text>{item.survey.title}: {item.survey.vacation_start} to {item.survey.vacation_end}. {item.defaulted ? "Defaulted to No" : item.response ? `Response: ${item.response}` : "Do you need mess food?"}</Text>
        {!item.response && !item.defaulted && <Group gap="xs"><Button size="xs" onClick={() => respond.mutate({ surveyId: item.survey.id, response: "yes" })}>Yes</Button><Button size="xs" variant="light" onClick={() => respond.mutate({ surveyId: item.survey.id, response: "no" })}>No</Button></Group>}</Group>)}
      {(surveys.data?.length ?? 0) === 0 && <Text c="dimmed">No survey is available for your registration.</Text>}
      {respond.error && <Text c="red">{errorMessage(respond.error)}</Text>}
    </Card>}
    {can("mms.feedback.self") && <Card withBorder mb="md"><Stack><Title order={4}>Mess feedback</Title>
      <TextInput label="Feedback" value={feedbackText} onChange={(event) => setFeedbackText(event.currentTarget.value)} />
      <Button disabled={!feedbackText.trim() || submitFeedback.isPending} onClick={() => submitFeedback.mutate()}>Send feedback</Button>
      {submitFeedback.error && <Text c="red">{errorMessage(submitFeedback.error)}</Text>}
      {feedback.data?.map((entry) => <Text key={entry.id} size="sm">{entry.text}</Text>)}
    </Stack></Card>}
    {can("mms.announcement.view") && <Card withBorder mb="md"><Title order={4} mb="sm">Announcements</Title>
      {announcements.data?.map((item) => <Stack key={item.id} gap={2} mb="sm"><Text fw={600}>{item.title}</Text><Text>{item.body}</Text></Stack>)}
      {(announcements.data?.length ?? 0) === 0 && <Text c="dimmed">No mess announcements.</Text>}
    </Card>}
    {can("mms.menu.view") && <Card withBorder><Title order={4} mb="sm">Weekly menu</Title>
      {(menu.data?.length ?? 0) === 0 ? <Text c="dimmed">No menu has been published.</Text> : <Table><Table.Thead><Table.Tr><Table.Th>Week</Table.Th><Table.Th>Day</Table.Th><Table.Th>Meal</Table.Th><Table.Th>Menu item</Table.Th></Table.Tr></Table.Thead>
        <Table.Tbody>{menu.data?.map((item) => <Table.Tr key={item.id}><Table.Td>{item.week_start}</Table.Td><Table.Td>{weekdays[item.day] ?? item.day}</Table.Td><Table.Td>{item.meal}</Table.Td><Table.Td>{item.item}</Table.Td></Table.Tr>)}</Table.Tbody></Table>}</Card>}
  </Container>;
}
