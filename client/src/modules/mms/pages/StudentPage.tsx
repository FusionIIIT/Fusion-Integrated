import { useState } from "react";
import {
  Alert, Badge, Button, Card, Container, Group, Select, SimpleGrid, Stack,
  Table, Text, TextInput, Textarea, Title,
} from "@mantine/core";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useMmsAction, useMmsData, type ListResult, type MmsBill, type MenuWeek,
  type StudentRequest, type VacationSurvey,
} from "../api";

interface WindowRow {
  id: number;
  cycle: string;
  is_open: boolean;
}

interface StudentStatus {
  registered: boolean;
}

interface RebateRow {
  id: number;
  reason: string;
  starts_on: string;
  ends_on: string;
  status: string;
  history: { status: string; at: string }[];
}

interface SpecialFoodRow {
  id: number;
  reason: string;
  requested_for: string;
  status: string;
  history: { status: string; at: string }[];
}

interface AnnouncementRow {
  id: number;
  title: string;
  body: string;
  published_at: string;
}

const DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
  "Saturday", "Sunday"];

function Rows<T extends { id: number }>({ rows, render }: {
  rows: T[];
  render: (row: T) => React.ReactNode;
}) {
  if (!rows.length) return <Text c="dimmed" size="sm">Nothing to show yet.</Text>;
  return <Stack gap="sm">{rows.map((row) => <Card key={row.id} withBorder padding="sm">
    {render(row)}
  </Card>)}</Stack>;
}

export default function StudentPage() {
  const { can } = useAuth();
  const student = can("mess_management.student.use");
  const windows = useMmsData<ListResult<WindowRow>>("registration-windows", student);
  const status = useMmsData<StudentStatus>("student-status", student);
  const requests = useMmsData<ListResult<StudentRequest>>("requests", student);
  const menus = useMmsData<ListResult<MenuWeek>>("menu", student);
  const rebates = useMmsData<ListResult<RebateRow>>("rebates", student);
  const surveys = useMmsData<ListResult<VacationSurvey>>("vacation-surveys", student);
  const specialFood = useMmsData<ListResult<SpecialFoodRow>>("special-food", student);
  const bills = useMmsData<ListResult<MmsBill> & { balance: string }>("bills", student);
  const announcements = useMmsData<ListResult<AnnouncementRow>>("announcements", student);
  const feedback = useMmsData<ListResult<{ id: number; message: string; created_at: string }>>(
    "feedback", student);
  const requestsAction = useMmsAction("requests");
  const rebateAction = useMmsAction("rebates");
  const specialAction = useMmsAction("special-food");
  const feedbackAction = useMmsAction("feedback");
  const [windowId, setWindowId] = useState<string | null>(null);
  const [rebateReason, setRebateReason] = useState<string | null>("medical");
  const [rebateStart, setRebateStart] = useState("");
  const [rebateEnd, setRebateEnd] = useState("");
  const [explanation, setExplanation] = useState("");
  const [foodReason, setFoodReason] = useState<string | null>("illness");
  const [foodDate, setFoodDate] = useState("");
  const [foodDetails, setFoodDetails] = useState("");
  const [feedbackText, setFeedbackText] = useState("");

  if (!student) {
    return <Container size="lg"><PageHeader title="My Mess" />
      <Alert color="gray">This page is available to students.</Alert>
    </Container>;
  }
  const allQueries = [windows, status, requests, menus, rebates, surveys,
    specialFood, bills, announcements, feedback];
  const failed = allQueries.find((query) => query.error);
  if (failed?.error) {
    return <Container size="lg"><PageHeader title="My Mess" />
      <ErrorState error={failed.error} />
    </Container>;
  }
  const openWindows = windows.data?.results.filter((row) => row.is_open) ?? [];
  const currentWindow = windowId ?? (openWindows[0] ? String(openWindows[0].id) : null);

  return (
    <Container size="xl">
      <PageHeader title="My Mess" subtitle="Requests, weekly menu, bills and mess updates" />
      {allQueries.some((query) => query.isPending) &&
        <Alert color="blue">Loading your mess information…</Alert>}

      <SimpleGrid cols={{ base: 1, md: 2 }} mb="lg">
        <Card withBorder>
          <Title order={4} mb="xs">Registration</Title>
          <Text size="sm" mb="sm">
            {status.data?.registered ? "You are registered for mess service."
              : "You are not currently registered for mess service."}
          </Text>
          {!status.data?.registered && (
            <Group align="end">
              <Select label="Open registration cycle" data={openWindows.map((row) => ({
                value: String(row.id), label: row.cycle,
              }))} value={currentWindow} onChange={setWindowId} />
              <Button disabled={!currentWindow || requestsAction.isPending}
                onClick={() => requestsAction.mutate({
                  body: { kind: "registration", window_id: Number(currentWindow) },
                })}>Submit registration</Button>
            </Group>
          )}
          {status.data?.registered && (
            <Button color="red" variant="light" loading={requestsAction.isPending}
              onClick={() => requestsAction.mutate({ body: { kind: "deregistration" } })}>
              Request deregistration
            </Button>
          )}
        </Card>

        <Card withBorder>
          <Title order={4} mb="xs">Submit a rebate request</Title>
          <Stack>
            <Select label="Reason" value={rebateReason} onChange={setRebateReason}
              data={[{ value: "medical", label: "Medical" },
                { value: "institute_leave", label: "Institute leave" },
                { value: "family_function", label: "Family function" },
                { value: "other", label: "Other" }]} />
            {rebateReason === "other" &&
              <Textarea label="Explanation" value={explanation}
                onChange={(event) => setExplanation(event.currentTarget.value)} />}
            <Group grow>
              <TextInput type="date" label="Start date" value={rebateStart}
                onChange={(event) => setRebateStart(event.currentTarget.value)} />
              <TextInput type="date" label="End date" value={rebateEnd}
                onChange={(event) => setRebateEnd(event.currentTarget.value)} />
            </Group>
            <Button loading={rebateAction.isPending} onClick={() => rebateAction.mutate({
              body: { reason: rebateReason, explanation, starts_on: rebateStart,
                ends_on: rebateEnd },
            })}>Submit rebate</Button>
          </Stack>
        </Card>
      </SimpleGrid>

      <SimpleGrid cols={{ base: 1, md: 2 }} mb="lg">
        <Card withBorder>
          <Title order={4} mb="sm">Special food request</Title>
          <Stack>
            <Select label="Reason" value={foodReason} onChange={setFoodReason}
              data={[{ value: "illness", label: "Illness" },
                { value: "personal_event", label: "Personal event" }]} />
            <TextInput type="date" label="Requested date" value={foodDate}
              onChange={(event) => setFoodDate(event.currentTarget.value)} />
            <Textarea label="Details" value={foodDetails}
              onChange={(event) => setFoodDetails(event.currentTarget.value)} />
            <Button loading={specialAction.isPending} onClick={() => specialAction.mutate({
              body: { reason: foodReason, requested_for: foodDate, details: foodDetails },
            })}>Submit special food request</Button>
          </Stack>
        </Card>

        <Card withBorder>
          <Title order={4} mb="sm">Feedback</Title>
          <Stack>
            <Textarea label="Mess service feedback" value={feedbackText}
              onChange={(event) => setFeedbackText(event.currentTarget.value)} />
            <Button loading={feedbackAction.isPending} onClick={() => feedbackAction.mutate({
              body: { message: feedbackText },
            })}>Submit feedback</Button>
            <Rows rows={feedback.data?.results ?? []} render={(row) =>
              <Text size="sm">{row.message}</Text>} />
          </Stack>
        </Card>
      </SimpleGrid>

      <SimpleGrid cols={{ base: 1, md: 2 }} mb="lg">
        <Card withBorder>
          <Title order={4} mb="sm">My requests</Title>
          <Rows rows={requests.data?.results ?? []} render={(row) => (
            <Stack gap={4}>
              <Group justify="space-between">
                <Text fw={600}>{row.kind === "registration" ? "Registration" : "Deregistration"}</Text>
                <Badge>{row.status.replaceAll("_", " ")}</Badge>
              </Group>
              <Text size="xs" c="dimmed">Submitted {new Date(row.created_at).toLocaleString()}</Text>
              {row.effective_at && <Text size="sm">Effective {new Date(row.effective_at).toLocaleString()}</Text>}
              <Text size="xs">{row.history.map((item) => item.status).join(" → ")}</Text>
            </Stack>
          )} />
          <Title order={5} mt="lg" mb="sm">Rebates</Title>
          <Rows rows={rebates.data?.results ?? []} render={(row) => (
            <Stack gap={4}>
              <Group justify="space-between">
                <Text size="sm">{row.reason}: {row.starts_on} to {row.ends_on}</Text>
                <Badge>{row.status}</Badge>
              </Group>
              <Text size="xs" c="dimmed">
                {row.history.map((item) =>
                  `${item.status} · ${new Date(item.at).toLocaleString()}`).join(" → ")}
              </Text>
            </Stack>
          )} />
          <Title order={5} mt="lg" mb="sm">Special food</Title>
          <Rows rows={specialFood.data?.results ?? []} render={(row) => (
            <Stack gap={4}>
              <Group justify="space-between">
                <Text size="sm">{row.reason}: {row.requested_for}</Text>
                <Badge>{row.status}</Badge>
              </Group>
              <Text size="xs" c="dimmed">
                {row.history.map((item) =>
                  `${item.status} · ${new Date(item.at).toLocaleString()}`).join(" → ")}
              </Text>
            </Stack>
          )} />
        </Card>

        <Card withBorder>
          <Title order={4} mb="sm">Vacation food continuity</Title>
          <Rows rows={surveys.data?.results ?? []} render={(survey) => (
            <VacationSurveyCard key={survey.id} survey={survey} />
          )} />
          <Title order={4} mt="lg" mb="sm">Monthly bills</Title>
          <Text fw={600} mb="sm">Outstanding MMS balance: ₹{bills.data?.balance ?? "0.00"}</Text>
          <Rows rows={bills.data?.results ?? []} render={(bill) => (
            <Group justify="space-between">
              <Text size="sm">{bill.month}/{bill.year}</Text>
              <Text size="sm">₹{bill.total}</Text>
              <Badge>{bill.status}</Badge>
            </Group>
          )} />
        </Card>
      </SimpleGrid>

      <Card withBorder mb="lg">
        <Title order={4} mb="sm">Weekly menus</Title>
        <Rows rows={menus.data?.results ?? []} render={(week) => (
          <Stack gap="xs">
            <Text fw={600}>Week of {week.week_start}</Text>
            <Table.ScrollContainer minWidth={500}>
              <Table>
                <Table.Thead><Table.Tr><Table.Th>Day</Table.Th>
                  <Table.Th>Breakfast</Table.Th><Table.Th>Lunch</Table.Th>
                  <Table.Th>Dinner</Table.Th></Table.Tr></Table.Thead>
                <Table.Tbody>{DAY_NAMES.map((day, index) => (
                  <Table.Tr key={day}><Table.Td>{day}</Table.Td>
                    {["breakfast", "lunch", "dinner"].map((meal) => (
                      <Table.Td key={meal}>{week.entries.find((entry) =>
                        entry.day === index && entry.meal === meal)?.item ?? "—"}</Table.Td>
                    ))}
                  </Table.Tr>
                ))}</Table.Tbody>
              </Table>
            </Table.ScrollContainer>
          </Stack>
        )} />
      </Card>

      <Card withBorder>
        <Title order={4} mb="sm">Announcements</Title>
        <Rows rows={announcements.data?.results ?? []} render={(row) => (
          <Stack gap={2}><Text fw={600}>{row.title}</Text>
            <Text size="sm">{row.body}</Text>
            <Text size="xs" c="dimmed">{new Date(row.published_at).toLocaleString()}</Text>
          </Stack>
        )} />
      </Card>
    </Container>
  );
}

function VacationSurveyCard({ survey }: { survey: VacationSurvey }) {
  const action = useMmsAction(`vacation-surveys/${survey.id}/responses`);
  const response = useMmsData<ListResult<{ response: string; is_default: boolean }>>(
    `vacation-surveys/${survey.id}/responses`);
  return (
    <Stack gap="xs">
      <Text fw={600}>{survey.title}</Text>
      <Text size="xs" c="dimmed">
        {survey.vacation_starts_on} – {survey.vacation_ends_on}; respond by {survey.deadline}
      </Text>
      <Group>
        <Button size="xs" variant="light" loading={action.isPending}
          onClick={() => action.mutate({ body: { response: "yes" } })}>Yes</Button>
        <Button size="xs" variant="light" color="gray" loading={action.isPending}
          onClick={() => action.mutate({ body: { response: "no" } })}>No</Button>
        {response.isError && <Text size="xs" c="red">{errorMessage(response.error)}</Text>}
        {response.data?.results[0] && <Badge>
          Response: {response.data.results[0].response}
          {response.data.results[0].is_default ? " (default)" : ""}
        </Badge>}
      </Group>
    </Stack>
  );
}
