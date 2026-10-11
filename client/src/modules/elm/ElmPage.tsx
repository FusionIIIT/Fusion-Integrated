import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  Badge,
  Button,
  Card,
  Container,
  Group,
  Loader,
  Select,
  Stack,
  Switch,
  Table,
  Text,
  Textarea,
  TextInput,
  Title,
} from "@mantine/core";
import { errorMessage, http } from "../../lib/http";

type View = "apply" | "mine" | "balance" | "approvals" | "admin";
type Item = Record<string, unknown>;
type Submission = { path: string; body: Item };

const TITLES: Record<View, string> = {
  apply: "Apply for Leave",
  mine: "My Leave Applications",
  balance: "My Leave Balances",
  approvals: "Assigned Leave Approvals",
  admin: "Leave Administration",
};

const LEAVE_TYPES = [
  { value: "CL", label: "Casual Leave" },
  { value: "RH", label: "Restricted Holiday" },
  { value: "SCL", label: "Special Casual Leave" },
  { value: "EL", label: "Earned Leave" },
  { value: "COL", label: "Commuted Leave" },
  { value: "VL", label: "Vacation Leave" },
];

const formatValue = (val: unknown) =>
  val == null ? "—" : typeof val === "object" ? JSON.stringify(val) : String(val);

function DataTable({
  rows,
  actions,
}: {
  rows: Item[];
  actions?: (item: Item) => React.ReactNode;
}) {
  const first = rows[0];
  if (!first) return <Text c="dimmed" size="sm">No entries yet.</Text>;
  return (
    <Table.ScrollContainer minWidth={650}>
      <Table striped highlightOnHover withTableBorder>
        <Table.Thead>
          <Table.Tr>
            {Object.keys(first).map((k) => (
              <Table.Th key={k}>{k.replaceAll("_", " ")}</Table.Th>
            ))}
            {actions && <Table.Th>Actions</Table.Th>}
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {rows.map((row, index) => (
            <Table.Tr key={formatValue(row.id ?? index)}>
              {Object.keys(first).map((key) => (
                <Table.Td key={key} style={{ overflowWrap: "anywhere" }}>
                  {key === "status" ? (
                    <Badge variant="light">{formatValue(row[key])}</Badge>
                  ) : (
                    <Text size="xs">{formatValue(row[key])}</Text>
                  )}
                </Table.Td>
              ))}
              {actions && <Table.Td>{actions(row)}</Table.Td>}
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  );
}

export default function ElmPage({ view }: { view: View }) {
  const queryClient = useQueryClient();
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [category, setCategory] = useState("CL");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [halfDay, setHalfDay] = useState("NONE");
  const [reason, setReason] = useState("");
  const [stationLeave, setStationLeave] = useState(false);
  const [stationLocation, setStationLocation] = useState("");
  const [substituteId, setSubstituteId] = useState("");
  const [remarks, setRemarks] = useState("");
  const [userId, setUserId] = useState("");
  const [kind, setKind] = useState("staff");
  const [unit, setUnit] = useState("");
  const [designation, setDesignation] = useState("");
  const [headId, setHeadId] = useState("");
  const [authorityId, setAuthorityId] = useState("");
  const [allotted, setAllotted] = useState("");
  const [year, setYear] = useState(String(new Date().getFullYear()));
  const [holidayDate, setHolidayDate] = useState("");
  const [holidayName, setHolidayName] = useState("");
  const [holidayKind, setHolidayKind] = useState("RH");
  const [published, setPublished] = useState(false);

  const query = useQuery({
    queryKey: ["leave-elm", view],
    retry: false,
    queryFn: async (): Promise<Item> => {
      if (view === "admin") {
        const [profiles, holidays] = await Promise.all([
          http.get("/elm/admin/profiles"),
          http.get("/elm/admin/holidays"),
        ]);
        return {
          profiles: profiles.data.results,
          holidays: holidays.data.results,
        };
      }
      if (view === "apply") {
        return { types: (await http.get("/elm/types")).data };
      }
      const endpoints: Record<"mine" | "balance" | "approvals", string> = {
        mine: "/elm/applications",
        balance: "/elm/balances",
        approvals: "/elm/approvals",
      };
      return (await http.get<Item>(endpoints[view])).data;
    },
  });

  const mutation = useMutation({
    mutationFn: async ({ path, body }: Submission) =>
      (await http.post(path, body)).data,
    onSuccess: async () => {
      setError("");
      setNotice("Saved successfully.");
      await queryClient.invalidateQueries({ queryKey: ["leave-elm"] });
    },
    onError: (err: unknown) => {
      setNotice("");
      setError(errorMessage(err));
    },
  });

  const submit = (path: string, body: Item) => {
    setError("");
    setNotice("");
    mutation.mutate({ path, body });
  };

  const results = (key: string): Item[] => {
    const rows = query.data?.[key];
    return Array.isArray(rows) ? (rows as Item[]) : [];
  };

  const actions = (item: Item) => {
    const status = String(item.status);
    const options =
      status === "AWAITING_SUB"
        ? ["accept_substitute", "decline_substitute"]
        : status === "RECOMMENDED" || ["CL", "RH"].includes(String(item.category))
          ? ["approve", "reject"]
          : ["recommend", "not_recommend"];
    return (
      <Group gap="xs" wrap="nowrap">
        {options.map((action) => (
          <Button
            key={action}
            size="xs"
            variant="light"
            loading={mutation.isPending}
            onClick={() =>
              submit(`/elm/applications/${item.id}/decide`, { action, remarks })
            }
          >
            {action.replaceAll("_", " ")}
          </Button>
        ))}
      </Group>
    );
  };

  return (
    <Container size="xl" py="lg">
      <Stack gap="lg">
        <Title order={2}>{TITLES[view]}</Title>
        {error && <Alert color="red">{error}</Alert>}
        {notice && <Alert color="green">{notice}</Alert>}
        {query.isPending && <Loader size="sm" />}
        {query.isError && <Alert color="red">{errorMessage(query.error)}</Alert>}
        {view === "apply" && (
          <Card withBorder>
            <Stack>
              <Select
                label="Leave type"
                data={LEAVE_TYPES}
                value={category}
                onChange={(v) => setCategory(v ?? "CL")}
              />
              <Group grow>
                <TextInput
                  label="Start date"
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.currentTarget.value)}
                />
                <TextInput
                  label="End date"
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.currentTarget.value)}
                />
              </Group>
              {category === "CL" && (
                <Select
                  label="Leave portion"
                  data={[
                    { value: "NONE", label: "Full day" },
                    { value: "FIRST", label: "First half" },
                    { value: "SECOND", label: "Second half" },
                  ]}
                  value={halfDay}
                  onChange={(v) => setHalfDay(v ?? "NONE")}
                />
              )}
              <Textarea
                label="Purpose / reason"
                value={reason}
                onChange={(e) => setReason(e.currentTarget.value)}
              />
              <TextInput
                label="Substitute IAM user ID (optional)"
                type="number"
                value={substituteId}
                onChange={(e) => setSubstituteId(e.currentTarget.value)}
              />
              <Switch
                label="Station Leave (outside headquarters)"
                checked={stationLeave}
                onChange={(e) => setStationLeave(e.currentTarget.checked)}
              />
              {stationLeave && (
                <TextInput
                  label="Station Leave destination"
                  value={stationLocation}
                  onChange={(e) => setStationLocation(e.currentTarget.value)}
                />
              )}
              <Button
                loading={mutation.isPending}
                onClick={() =>
                  submit("/elm/applications", {
                    category,
                    start_date: startDate,
                    end_date: endDate,
                    reason,
                    half_day: category === "CL" ? halfDay : "NONE",
                    station_leave: stationLeave,
                    station_location: stationLocation,
                    substitute_user_id: substituteId ? Number(substituteId) : null,
                  })
                }
              >
                Submit application
              </Button>
            </Stack>
          </Card>
        )}
        {view === "mine" && (
          <DataTable
            rows={results("results")}
            actions={(item) => {
              const status = String(item.status);
              if (["AWAITING_SUB", "PENDING", "RECOMMENDED"].includes(status)) {
                return (
                  <Button
                    size="xs"
                    variant="light"
                    color="red"
                    loading={mutation.isPending}
                    onClick={() => submit(`/elm/applications/${item.id}/withdraw`, {})}
                  >
                    Withdraw
                  </Button>
                );
              }
              if (status === "APPROVED") {
                return (
                  <Button
                    size="xs"
                    variant="light"
                    color="orange"
                    loading={mutation.isPending}
                    onClick={() => submit(`/elm/applications/${item.id}/cancel`, {})}
                  >
                    Cancel
                  </Button>
                );
              }
              return null;
            }}
          />
        )}
        {view === "balance" && <DataTable rows={results("results")} />}
        {view === "approvals" && (
          <Stack>
            <Textarea
              label="Decision remarks"
              value={remarks}
              onChange={(e) => setRemarks(e.currentTarget.value)}
            />
            <DataTable rows={results("results")} actions={actions} />
          </Stack>
        )}
        {view === "admin" && (
          <Stack>
            <Card withBorder>
              <Stack>
                <Title order={4}>Employee profile and approval authorities</Title>
                <Group grow>
                  <TextInput
                    label="IAM user ID"
                    type="number"
                    value={userId}
                    onChange={(e) => setUserId(e.currentTarget.value)}
                  />
                  <Select
                    label="Employee category"
                    data={["faculty", "staff"]}
                    value={kind}
                    onChange={(v) => setKind(v ?? "staff")}
                  />
                </Group>
                <Group grow>
                  <TextInput
                    label="Unit / department"
                    value={unit}
                    onChange={(e) => setUnit(e.currentTarget.value)}
                  />
                  <TextInput
                    label="Designation"
                    value={designation}
                    onChange={(e) => setDesignation(e.currentTarget.value)}
                  />
                </Group>
                <Group grow>
                  <TextInput
                    label="Unit Head IAM user ID"
                    value={headId}
                    onChange={(e) => setHeadId(e.currentTarget.value)}
                  />
                  <TextInput
                    label="Higher sanction IAM user ID"
                    value={authorityId}
                    onChange={(e) => setAuthorityId(e.currentTarget.value)}
                  />
                </Group>
                <Button
                  loading={mutation.isPending}
                  onClick={() =>
                    submit("/elm/admin/profiles", {
                      user_id: Number(userId),
                      employee_kind: kind,
                      unit,
                      designation,
                      unit_head_user_id: headId ? Number(headId) : null,
                      sanction_authority_user_id: authorityId ? Number(authorityId) : null,
                    })
                  }
                >
                  Save employee routing profile
                </Button>
                <DataTable rows={results("profiles")} />
              </Stack>
            </Card>
            <Card withBorder>
              <Stack>
                <Title order={4}>Allot leave balance</Title>
                <Group grow>
                  <Select
                    label="Leave type"
                    data={LEAVE_TYPES}
                    value={category}
                    onChange={(v) => setCategory(v ?? "CL")}
                  />
                  <TextInput
                    label="Year"
                    type="number"
                    value={year}
                    onChange={(e) => setYear(e.currentTarget.value)}
                  />
                  <TextInput
                    label="Allotted days"
                    type="number"
                    value={allotted}
                    onChange={(e) => setAllotted(e.currentTarget.value)}
                  />
                </Group>
                <Button
                  loading={mutation.isPending}
                  onClick={() =>
                    submit("/elm/admin/balances", {
                      employee_id: Number(userId),
                      category,
                      year: Number(year),
                      allotted: Number(allotted),
                    })
                  }
                >
                  Save allotment
                </Button>
              </Stack>
            </Card>
            <Card withBorder>
              <Stack>
                <Title order={4}>Holiday and vacation calendar dates</Title>
                <Group grow>
                  <TextInput
                    label="Date"
                    type="date"
                    value={holidayDate}
                    onChange={(e) => setHolidayDate(e.currentTarget.value)}
                  />
                  <TextInput
                    label="Name"
                    value={holidayName}
                    onChange={(e) => setHolidayName(e.currentTarget.value)}
                  />
                  <Select
                    label="Date category"
                    data={["RH", "CLOSED", "VACATION"]}
                    value={holidayKind}
                    onChange={(v) => setHolidayKind(v ?? "RH")}
                  />
                </Group>
                <Switch
                  label="Published / active"
                  checked={published}
                  onChange={(e) => setPublished(e.currentTarget.checked)}
                />
                <Button
                  loading={mutation.isPending}
                  onClick={() =>
                    submit("/elm/admin/holidays", {
                      date: holidayDate,
                      name: holidayName,
                      kind: holidayKind,
                      published,
                    })
                  }
                >
                  Save calendar date
                </Button>
                <DataTable rows={results("holidays")} />
              </Stack>
            </Card>
          </Stack>
        )}
      </Stack>
    </Container>
  );
}
