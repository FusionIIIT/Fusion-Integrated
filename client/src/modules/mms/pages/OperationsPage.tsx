import { useEffect, useMemo, useState } from "react";
import {
  Alert, Badge, Button, Card, Container, Group, NumberInput, Select,
  SimpleGrid, Stack, Table, Text, TextInput, Textarea, Title,
} from "@mantine/core";

import { useAuth } from "../../../auth/AuthProvider";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useMmsAction, useMmsData, type ListResult, type MmsBill, type MenuWeek,
  type Overview, type StudentRequest, type VacationSurvey,
} from "../api";

const MEALS = ["breakfast", "lunch", "dinner"] as const;
const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
  "Saturday", "Sunday"];
type MenuInput = { day: number; meal: string; item: string };
interface BillingInput {
  user_id: number;
  served_days: number | null;
  daily_rate: string | null;
}
interface RegistrationWindow {
  id: number;
  cycle: string;
  opens_at: string;
  closes_at: string;
  is_open: boolean;
}

export default function OperationsPage() {
  const { can } = useAuth();
  const mayView = can("mess_management.operations.view");
  const caretakerPermission = can("mess_management.requests.review");
  const wardenPermission = can("mess_management.reports.warden");
  const overview = useMmsData<Overview>("overview", mayView);
  const caretaker = caretakerPermission
    && Boolean(overview.data?.active_roles.includes("caretaker"));
  const warden = wardenPermission
    && Boolean(overview.data?.active_roles.includes("warden"));
  const menu = useMmsData<ListResult<MenuWeek>>("menu", mayView);
  const windows = useMmsData<ListResult<RegistrationWindow>>(
    "registration-windows", mayView);
  const bills = useMmsData<ListResult<MmsBill>>("bills",
    can("mess_management.billing.manage"));
  const windowAction = useMmsAction("registration-windows");
  const requestAction = useMmsAction("requests");
  const rebateAction = useMmsAction("rebates");
  const specialAction = useMmsAction("special-food");
  const surveyAction = useMmsAction("vacation-surveys");
  const announcementAction = useMmsAction("announcements");
  const menuAction = useMmsAction("menu");
  const billAction = useMmsAction("bills");
  const billingInputAction = useMmsAction("billing-inputs");
  const [cycle, setCycle] = useState("");
  const [windowOpens, setWindowOpens] = useState("");
  const [windowCloses, setWindowCloses] = useState("");
  const [weekStart, setWeekStart] = useState("");
  const [menuItems, setMenuItems] = useState<MenuInput[]>(() =>
    DAYS.flatMap((_, day) => MEALS.map((meal) => ({ day, meal, item: "" }))));
  const [surveyTitle, setSurveyTitle] = useState("");
  const [vacationStart, setVacationStart] = useState("");
  const [vacationEnd, setVacationEnd] = useState("");
  const [surveyDeadline, setSurveyDeadline] = useState("");
  const [announcementTitle, setAnnouncementTitle] = useState("");
  const [announcementBody, setAnnouncementBody] = useState("");
  const [decisionCharges, setDecisionCharges] = useState<Record<number, string>>({});
  const [report, setReport] = useState<string | null>(null);
  const [reportSearch, setReportSearch] = useState("");
  const now = new Date();
  const [billingYear, setBillingYear] = useState(String(now.getFullYear()));
  const [billingMonth, setBillingMonth] = useState(String(now.getMonth() + 1));
  const inputPath = `billing-students?year=${billingYear}&month=${billingMonth}`;
  const billable = useMmsData<ListResult<BillingInput>>(inputPath,
    can("mess_management.billing.manage"));
  const [billingInputs, setBillingInputs] = useState<BillingInput[] | null>(null);
  useEffect(() => setBillingInputs(null), [inputPath]);
  useEffect(() => {
    const week = menu.data?.results.find((row) => row.week_start === weekStart);
    if (week) {
      setMenuItems(DAYS.flatMap((_, day) => MEALS.map((meal) => ({
        day, meal,
        item: week.entries.find((entry) => entry.day === day
          && entry.meal === meal)?.item ?? "",
      }))));
    }
  }, [menu.data, weekStart]);
  const reportQuery = useMmsData<ListResult<Record<string, unknown>>>(
    `reports?type=${report ?? ""}`, Boolean(report));
  const filteredReport = useMemo(() => {
    const rows = reportQuery.data?.results ?? [];
    if (!reportSearch.trim()) return rows;
    return rows.filter((row) => JSON.stringify(row).toLowerCase()
      .includes(reportSearch.toLowerCase()));
  }, [reportQuery.data, reportSearch]);
  const firstReportRow = filteredReport.at(0);

  if (!mayView) {
    return <Container size="lg"><PageHeader title="Mess Operations" />
      <Alert color="gray">Operational information is available to the active Caretaker and Warden.</Alert>
    </Container>;
  }
  if (overview.error) return <Container size="xl"><ErrorState error={overview.error} /></Container>;

  const requests = overview.data?.requests ?? [];
  const pendingRequests = requests.filter((request) => request.status === "pending");
  const activeInputs = billingInputs ?? billable.data?.results ?? [];

  function decideRequest(row: StudentRequest, approve: boolean) {
    requestAction.mutate({
      path: `requests/${row.id}/decision`, body: { approve },
    });
  }

  function updateMenu(index: number, item: string) {
    setMenuItems((current) => current.map((entry, i) =>
      i === index ? { ...entry, item } : entry));
  }

  function generateBills() {
    billingInputAction.mutate({
      body: { year: Number(billingYear), month: Number(billingMonth),
        students: activeInputs.map((entry) => ({
          user_id: entry.user_id, daily_rate: entry.daily_rate,
          served_days: entry.served_days,
        })) },
    });
  }

  return (
    <Container size="xl">
      <PageHeader title={warden ? "Mess Oversight" : "Mess Operations"}
        subtitle="Operational requests, reports and mess-service records" />
      {overview.isPending && <Alert color="blue">Loading operational records…</Alert>}
      {overview.data && (
        <SimpleGrid cols={{ base: 1, md: 3 }} mb="lg">
          <Card withBorder><Text size="sm" c="dimmed">Registered students</Text>
            <Title order={3}>{overview.data.enrollment_count}</Title></Card>
          <Card withBorder><Text size="sm" c="dimmed">Pending registration requests</Text>
            <Title order={3}>{pendingRequests.length}</Title></Card>
          <Card withBorder><Text size="sm" c="dimmed">Feedback entries</Text>
            <Title order={3}>{overview.data.feedback.length}</Title></Card>
        </SimpleGrid>
      )}
      {overview.data && !overview.data.special_food_auto_rejection_enabled &&
        <Alert color="yellow" mb="lg">
          Automatic special-food rejection is disabled until the institution configures its decision period.
        </Alert>}

      {caretaker && (
        <>
          <SimpleGrid cols={{ base: 1, md: 2 }} mb="lg">
            <Card withBorder>
              <Title order={4} mb="sm">Open registration window</Title>
              <Stack>
                <TextInput label="Mess cycle" value={cycle}
                  onChange={(event) => setCycle(event.currentTarget.value)} />
                <TextInput type="datetime-local" label="Opens at" value={windowOpens}
                  onChange={(event) => setWindowOpens(event.currentTarget.value)} />
                <TextInput type="datetime-local" label="Closes at" value={windowCloses}
                  onChange={(event) => setWindowCloses(event.currentTarget.value)} />
                <Button loading={windowAction.isPending} onClick={() =>
                  windowAction.mutate({ body: { cycle, opens_at: windowOpens,
                    closes_at: windowCloses } })}>Open window</Button>
              </Stack>
            </Card>
            <Card withBorder>
              <Title order={4} mb="sm">Publish an announcement</Title>
              <Stack>
                <TextInput label="Title" value={announcementTitle}
                  onChange={(event) => setAnnouncementTitle(event.currentTarget.value)} />
                <Textarea label="Announcement" value={announcementBody}
                  onChange={(event) => setAnnouncementBody(event.currentTarget.value)} />
                <Button loading={announcementAction.isPending} onClick={() =>
                  announcementAction.mutate({ body: { title: announcementTitle,
                    body: announcementBody } })}>Publish</Button>
              </Stack>
            </Card>
          </SimpleGrid>

          <Card withBorder mb="lg">
            <Title order={4} mb="sm">Weekly menu editor</Title>
            <Group align="end" mb="md">
              <TextInput type="date" label="Week starting" value={weekStart}
                onChange={(event) => setWeekStart(event.currentTarget.value)} />
              <Button loading={menuAction.isPending}
                disabled={!weekStart || menuItems.some((entry) => !entry.item.trim())}
                onClick={() =>
                menuAction.mutate({ body: { week_start: weekStart, entries: menuItems } })}>
                Publish weekly menu
              </Button>
            </Group>
            <Text size="xs" c="dimmed" mb="sm">
              Fill all 21 day-and-meal entries before publishing.
            </Text>
            <Table.ScrollContainer minWidth={700}>
              <Table>
                <Table.Thead><Table.Tr><Table.Th>Day</Table.Th>
                  {MEALS.map((meal) => <Table.Th key={meal}>{meal}</Table.Th>)}
                </Table.Tr></Table.Thead>
                <Table.Tbody>{DAYS.map((day, index) => (
                  <Table.Tr key={day}><Table.Td>{day}</Table.Td>
                    {MEALS.map((meal) => {
                      const row = menuItems.findIndex((entry) =>
                        entry.day === index && entry.meal === meal);
                      return <Table.Td key={meal}>
                        <TextInput aria-label={`${day} ${meal}`}
                          value={menuItems[row]?.item ?? ""}
                          onChange={(event) => updateMenu(row, event.currentTarget.value)} />
                      </Table.Td>;
                    })}
                  </Table.Tr>
                ))}</Table.Tbody>
              </Table>
            </Table.ScrollContainer>
          </Card>

          <SimpleGrid cols={{ base: 1, md: 2 }} mb="lg">
            <Card withBorder>
              <Title order={4} mb="sm">Vacation food continuity survey</Title>
              <Stack>
                <TextInput label="Survey title" value={surveyTitle}
                  onChange={(event) => setSurveyTitle(event.currentTarget.value)} />
                <Group grow>
                  <TextInput type="date" label="Vacation starts" value={vacationStart}
                    onChange={(event) => setVacationStart(event.currentTarget.value)} />
                  <TextInput type="date" label="Vacation ends" value={vacationEnd}
                    onChange={(event) => setVacationEnd(event.currentTarget.value)} />
                </Group>
                <TextInput type="datetime-local" label="Response deadline"
                  value={surveyDeadline}
                  onChange={(event) => setSurveyDeadline(event.currentTarget.value)} />
                <Button loading={surveyAction.isPending} onClick={() =>
                  surveyAction.mutate({ body: { title: surveyTitle,
                    vacation_starts_on: vacationStart, vacation_ends_on: vacationEnd,
                    deadline: surveyDeadline } })}>Create survey</Button>
                <Text size="xs" c="dimmed">
                  Reminders are triggered manually; the specification does not define a cadence.
                </Text>
              </Stack>
            </Card>
            <Card withBorder>
              <Title order={4} mb="sm">Survey reminders</Title>
              {(overview.data?.surveys ?? []).map((survey: VacationSurvey) => (
                <VacationSurveySummary key={survey.id} survey={survey}
                  caretaker={caretaker}
                  onRemind={() => surveyAction.mutate({
                    path: `vacation-surveys/${survey.id}/remind`,
                  })}
                  reminding={surveyAction.isPending} />
              ))}
              {!overview.data?.surveys.length && <Text size="sm" c="dimmed">No surveys.</Text>}
            </Card>
          </SimpleGrid>
        </>
      )}

      <Card withBorder mb="lg">
        <Title order={4} mb="sm">Registration windows</Title>
        {(windows.data?.results ?? []).map((row) => (
          <Group key={row.id} justify="space-between" mb="xs">
            <Text size="sm">{row.cycle} · {new Date(row.opens_at).toLocaleString()} – {
              new Date(row.closes_at).toLocaleString()}</Text>
            <Badge color={row.is_open ? "green" : "gray"}>
              {row.is_open ? "Open" : "Closed"}
            </Badge>
          </Group>
        ))}
        {!windows.data?.results.length &&
          <Text size="sm" c="dimmed">No registration windows have been configured.</Text>}
        {windows.isError && <ErrorState error={windows.error} />}
      </Card>

      <Card withBorder mb="lg">
        <Title order={4} mb="sm">Weekly menu</Title>
        {(menu.data?.results ?? []).map((week) => (
          <Stack key={week.id} gap="xs" mb="md">
            <Text fw={600}>Week of {week.week_start}</Text>
            <Table.ScrollContainer minWidth={600}><Table>
              <Table.Thead><Table.Tr><Table.Th>Day</Table.Th>
                {MEALS.map((meal) => <Table.Th key={meal}>{meal}</Table.Th>)}
              </Table.Tr></Table.Thead>
              <Table.Tbody>{DAYS.map((day, dayIndex) => (
                <Table.Tr key={day}><Table.Td>{day}</Table.Td>
                  {MEALS.map((meal) => <Table.Td key={meal}>
                    {week.entries.find((entry) => entry.day === dayIndex
                      && entry.meal === meal)?.item ?? "—"}
                  </Table.Td>)}
                </Table.Tr>
              ))}</Table.Tbody>
            </Table></Table.ScrollContainer>
          </Stack>
        ))}
        {!menu.data?.results.length && <Text size="sm" c="dimmed">No menu has been published.</Text>}
        {menu.isError && <ErrorState error={menu.error} />}
      </Card>

      <Card withBorder mb="lg">
        <Title order={4} mb="sm">Student requests for oversight</Title>
        {!requests.length && <Text size="sm" c="dimmed">No student requests.</Text>}
        <Stack>
          {requests.map((row) => <Group key={row.id} justify="space-between"
            align="center" wrap="nowrap">
            <Stack gap={2}>
              <Text size="sm" fw={600}>{row.kind} · Student {row.user_id}</Text>
              <Text size="xs" c="dimmed">{row.status.replaceAll("_", " ")} · {
                new Date(row.created_at).toLocaleString()}</Text>
            </Stack>
            <Group>
              <Badge>{row.status}</Badge>
              {caretaker && row.status === "pending" && <>
                <Button size="xs" color="green" loading={requestAction.isPending}
                  onClick={() => decideRequest(row, true)}>Approve</Button>
                <Button size="xs" color="red" variant="light"
                  loading={requestAction.isPending}
                  onClick={() => decideRequest(row, false)}>Reject</Button>
              </>}
            </Group>
          </Group>)}
        </Stack>
      </Card>

      <SimpleGrid cols={{ base: 1, md: 2 }} mb="lg">
        <Card withBorder>
          <Title order={4} mb="sm">Rebate requests</Title>
          {(overview.data?.rebates ?? []).map((row) => (
            <Group key={row.id} justify="space-between" mb="sm">
              <Text size="sm">Student {row.user_id} · {row.reason} · {row.starts_on} to {row.ends_on}</Text>
              <Group><Badge>{row.status}</Badge>
                {caretaker && row.status === "pending" && <>
                  <Button size="xs" onClick={() => rebateAction.mutate({
                    path: `rebates/${row.id}/decision`, body: { approve: true },
                  })}>Approve</Button>
                  <Button size="xs" color="red" variant="light" onClick={() =>
                    rebateAction.mutate({ path: `rebates/${row.id}/decision`,
                      body: { approve: false } })}>Reject</Button>
                </>}
              </Group>
            </Group>
          ))}
          {!overview.data?.rebates.length && <Text size="sm" c="dimmed">No rebate requests.</Text>}
        </Card>
        <Card withBorder>
          <Title order={4} mb="sm">Special food requests</Title>
          {(overview.data?.special_food ?? []).map((row) => (
            <Stack key={row.id} gap="xs" mb="md">
              <Group justify="space-between">
                <Text size="sm">Student {row.user_id} · {row.reason} · {row.requested_for}</Text>
                <Badge>{row.status}</Badge>
              </Group>
              <Text size="xs">{row.details}</Text>
              {caretaker && row.status === "requested" && (
                <Group>
                  <TextInput aria-label={`Charge for request ${row.id}`} placeholder="Policy-provided charge"
                    value={decisionCharges[row.id] ?? ""}
                    onChange={(event) => setDecisionCharges((current) => ({
                      ...current, [row.id]: event.currentTarget.value,
                    }))} />
                  <Button size="xs" loading={specialAction.isPending} onClick={() =>
                    specialAction.mutate({ path: `special-food/${row.id}/decision`,
                      body: { approve: true, charge_amount: decisionCharges[row.id] } })}>
                    Approve
                  </Button>
                  <Button size="xs" color="red" variant="light"
                    loading={specialAction.isPending} onClick={() =>
                      specialAction.mutate({ path: `special-food/${row.id}/decision`,
                        body: { approve: false } })}>Reject</Button>
                </Group>
              )}
              {caretaker && row.status === "approved" && (
                <Group>
                  <Button size="xs" onClick={() => specialAction.mutate({
                    path: `special-food/${row.id}/fulfillment`, body: { status: "served" },
                  })}>Mark served</Button>
                  <Button size="xs" variant="light" color="gray" onClick={() =>
                    specialAction.mutate({ path: `special-food/${row.id}/fulfillment`,
                      body: { status: "cancelled" } })}>Cancel</Button>
                </Group>
              )}
            </Stack>
          ))}
          {!overview.data?.special_food.length &&
            <Text size="sm" c="dimmed">No special food requests.</Text>}
        </Card>
      </SimpleGrid>

      {caretaker && (
        <Card withBorder mb="lg">
          <Title order={4} mb="sm">Monthly billing inputs</Title>
          <Group align="end" mb="md">
            <TextInput type="number" label="Year" value={billingYear}
              onChange={(event) => setBillingYear(event.currentTarget.value)} />
            <Select label="Month" value={billingMonth} onChange={(value) =>
              value && setBillingMonth(value)}
              data={Array.from({ length: 12 }, (_, index) => ({
                value: String(index + 1), label: new Date(2000, index).toLocaleString(
                  "en", { month: "long" }),
              }))} />
            <Button variant="light" onClick={() => {
              setBillingInputs(null);
              void billable.refetch();
            }}>Load registered students</Button>
          </Group>
          <Text size="xs" c="dimmed" mb="sm">
            Enter institution-provided daily rates and served-day counts. MMS does not define rates or attendance.
          </Text>
          {activeInputs.length > 0 && (
            <>
              <Table>
                <Table.Thead><Table.Tr><Table.Th>Student ID</Table.Th>
                  <Table.Th>Served days</Table.Th><Table.Th>Daily rate</Table.Th>
                </Table.Tr></Table.Thead>
                <Table.Tbody>{activeInputs.map((row, index) => (
                  <Table.Tr key={row.user_id}>
                    <Table.Td>{row.user_id}</Table.Td>
                    <Table.Td><NumberInput min={0} max={31} allowDecimal={false}
                      value={row.served_days ?? ""}
                      onChange={(value) => setBillingInputs((current) => {
                        const rows = current ?? activeInputs;
                        return rows.map((entry, i) => i === index
                          ? { ...entry, served_days: typeof value === "number" ? value : null }
                          : entry);
                      })} /></Table.Td>
                    <Table.Td><TextInput type="number" min={0} step="0.01"
                      value={row.daily_rate ?? ""}
                      onChange={(event) => setBillingInputs((current) => {
                        const rows = current ?? activeInputs;
                        return rows.map((entry, i) => i === index
                          ? { ...entry, daily_rate: event.currentTarget.value }
                          : entry);
                      })} /></Table.Td>
                  </Table.Tr>
                ))}</Table.Tbody>
              </Table>
              <Button mt="md" loading={billingInputAction.isPending}
                onClick={generateBills}>Save inputs for scheduled generation</Button>
              <Text size="xs" c="dimmed" mt="xs">
                Completed calendar-month bills are generated automatically after all inputs are available.
              </Text>
            </>
          )}
          {billable.data && activeInputs.length === 0 &&
            <Text size="sm" c="dimmed">No students are registered for the selected billing month.</Text>}
          {billable.isError && <ErrorState error={billable.error} />}
          {(overview.data?.special_food ?? []).some((row) =>
            row.status === "cancelled" && row.requested_for.startsWith(
              `${billingYear}-${billingMonth.padStart(2, "0")}-`)) &&
            <Alert color="yellow" mt="md">
              A cancelled special-food request has unresolved billing treatment. Only that student's bill is held for clarification; other students' bills can proceed.
            </Alert>}
        </Card>
      )}

      {caretaker && (
        <Card withBorder mb="lg">
          <Title order={4} mb="sm">Monthly bill review and publication</Title>
          {(bills.data?.results ?? []).map((bill) => (
            <Group key={bill.id} justify="space-between" mb="xs">
              <Text size="sm">Student {bill.user_id} · {bill.month}/{bill.year} · ₹{bill.total}</Text>
              <Group><Badge>{bill.status}</Badge>
                {bill.status === "generated" && <Button size="xs" onClick={() =>
                  billAction.mutate({ path: `bills/${bill.id}/finalize` })}>Finalize</Button>}
                {bill.status === "finalized" && <Button size="xs" onClick={() =>
                  billAction.mutate({ path: `bills/${bill.id}/publish` })}>Publish</Button>}
              </Group>
            </Group>
          ))}
          {!bills.data?.results.length && <Text size="sm" c="dimmed">No bills are ready for review.</Text>}
        </Card>
      )}

      <SimpleGrid cols={{ base: 1, md: 2 }} mb="lg">
        <Card withBorder>
          <Title order={4} mb="sm">Feedback</Title>
          {(overview.data?.feedback ?? []).map((row) => (
            <Stack key={row.id} gap={2} mb="sm">
              <Text size="sm">{row.message}</Text>
              <Text size="xs" c="dimmed">Student {row.user_id} · {row.created_at}</Text>
            </Stack>
          ))}
          {!overview.data?.feedback.length && <Text size="sm" c="dimmed">No feedback.</Text>}
        </Card>
        <Card withBorder>
          <Title order={4} mb="sm">Announcements history</Title>
          {(overview.data?.announcements ?? []).map((row) => (
            <Stack key={row.id} gap={2} mb="sm">
              <Text fw={600}>{row.title}</Text><Text size="sm">{row.body}</Text>
              <Text size="xs" c="dimmed">{row.published_at}</Text>
            </Stack>
          ))}
        </Card>
      </SimpleGrid>

      <Card withBorder>
        <Title order={4} mb="sm">{warden ? "Supervisory reports" : "Operational reports"}</Title>
        <Group align="end" mb="md">
          <Select label="Report" value={report} onChange={setReport}
            data={warden
              ? [{ value: "registered", label: "Registered students" },
                { value: "rebates", label: "Rebate summary" },
                { value: "vacation", label: "Vacation response summary" }]
              : [{ value: "registration_trends", label: "Registration trends" },
                { value: "special_meals", label: "Special meal log" },
                { value: "billing_summary", label: "Billing summary" }]} />
          {warden && <TextInput label="Search report" value={reportSearch}
            onChange={(event) => setReportSearch(event.currentTarget.value)} />}
        </Group>
        {reportQuery.isError && <ErrorState error={reportQuery.error} />}
        {report && !reportQuery.isPending && (
          firstReportRow
            ? <Table.ScrollContainer minWidth={600}><Table>
              <Table.Thead><Table.Tr>{Object.keys(firstReportRow).map((key) =>
                <Table.Th key={key}>{key.replaceAll("_", " ")}</Table.Th>)}</Table.Tr></Table.Thead>
              <Table.Tbody>{filteredReport.map((row, index) =>
                <Table.Tr key={index}>{Object.values(row).map((value, cell) =>
                  <Table.Td key={cell}>{String(value ?? "")}</Table.Td>)}</Table.Tr>)}</Table.Tbody>
            </Table></Table.ScrollContainer>
            : <Text size="sm" c="dimmed">No report data matches.</Text>
        )}
      </Card>
    </Container>
  );
}

function VacationSurveySummary({ survey, caretaker, onRemind, reminding }: {
  survey: VacationSurvey;
  caretaker: boolean;
  onRemind: () => void;
  reminding: boolean;
}) {
  const responses = useMmsData<ListResult<{ response: string; user_id: number }>>(
    `vacation-surveys/${survey.id}/responses`);
  const yes = responses.data?.results.filter((row) => row.response === "yes").length ?? 0;
  const no = responses.data?.results.filter((row) => row.response === "no").length ?? 0;
  return (
    <Stack gap={4} mb="sm">
      <Group justify="space-between">
        <Text size="sm">{survey.title}</Text>
        {caretaker && <Button size="xs" variant="light" loading={reminding}
          onClick={onRemind}>Send reminder</Button>}
      </Group>
      <Text size="xs" c="dimmed">
        Responses: Yes {yes}, No {no}{responses.isPending ? " · loading" : ""}
      </Text>
      {responses.isError && <Text size="xs" c="red">Could not load survey responses.</Text>}
    </Stack>
  );
}
