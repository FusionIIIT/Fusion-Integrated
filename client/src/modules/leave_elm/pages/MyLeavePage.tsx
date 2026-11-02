import { useCallback, useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import {
  Alert, Button, Card, Checkbox, Container, Group, Select, Stack, Table,
  Text, TextInput, Textarea,
} from "@mantine/core";
import { DateInput } from "@mantine/dates";
import { notifications } from "@mantine/notifications";

import { errorMessage, http } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";

type LeaveBalance = {
  category: string;
  category_label: string;
  year: number;
  entitlement: string;
  carried_in: string;
  converted_in: string;
  used: string;
  remaining: string;
  available: string;
};

type LeaveApplication = {
  id: number;
  category: string;
  request_type: string;
  status: string;
  start_date: string;
  end_date: string;
  half_day_period: string;
  reason: string;
  station_leave: boolean;
  decision_note: string;
};

const categories = [
  { value: "CL", label: "Casual Leave (CL)" },
  { value: "RH", label: "Restricted Holiday (RH)" },
  { value: "SCL", label: "Special Casual Leave (SCL)" },
  { value: "EL", label: "Earned Leave (EL)" },
  { value: "COL", label: "Commuted Leave (COL)" },
  { value: "VL", label: "Vacation Leave (VL)" },
];

function isoDate(value: Date | null) {
  if (!value) return "";
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${value.getFullYear()}-${month}-${day}`;
}

export default function MyLeavePage({ showApplicationForm = false }: {
  showApplicationForm?: boolean;
}) {
  const [balances, setBalances] = useState<LeaveBalance[]>([]);
  const [applications, setApplications] = useState<LeaveApplication[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [category, setCategory] = useState<string | null>("CL");
  const [startDate, setStartDate] = useState<Date | null>(null);
  const [endDate, setEndDate] = useState<Date | null>(null);
  const [halfDay, setHalfDay] = useState("full");
  const [reason, setReason] = useState("");
  const [stationLeave, setStationLeave] = useState(false);
  const [destination, setDestination] = useState("");
  const [evidence, setEvidence] = useState("");
  const [substituteId, setSubstituteId] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [extensionEnd, setExtensionEnd] = useState<Date | null>(null);
  const [extensionSubstituteId, setExtensionSubstituteId] = useState("");
  const [resumeDate, setResumeDate] = useState<Date | null>(null);
  const [resumeDetails, setResumeDetails] = useState("");
  const [busy, setBusy] = useState(false);

  const reload = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [balanceResponse, applicationResponse] = await Promise.all([
        http.get<LeaveBalance[]>("/leave/balances"),
        http.get<{ results: LeaveApplication[] }>("/leave/applications"),
      ]);
      setBalances(balanceResponse.data);
      setApplications(applicationResponse.data.results);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void reload(); }, [reload]);

  const selectableApplications = useMemo(
    () => applications.filter((row) => row.status === "approved"),
    [applications],
  );

  async function submitApplication(event: FormEvent) {
    event.preventDefault();
    if (!category || !startDate || !endDate) return;
    setBusy(true);
    try {
      await http.post("/leave/applications/apply", {
        category,
        start_date: isoDate(startDate),
        end_date: isoDate(endDate),
        half_day_period: category === "CL" ? halfDay : "full",
        reason,
        station_leave: stationLeave,
        station_destination: destination,
        evidence_reference: evidence,
        substitute_user_id: substituteId ? Number(substituteId) : null,
      });
      notifications.show({ color: "green", title: "Submitted", message: "Leave request submitted." });
      setReason("");
      setEvidence("");
      setSubstituteId("");
      await reload();
    } catch (e) {
      notifications.show({ color: "red", title: "Could not submit", message: errorMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  async function submitAction(path: string, payload?: object) {
    if (selectedId) await submitActionFor(selectedId, path, payload);
  }

  async function submitActionFor(id: number | string, path: string, payload?: object) {
    setBusy(true);
    try {
      await http.post(`/leave/applications/${id}/${path}`, payload ?? {});
      notifications.show({ color: "green", title: "Request submitted", message: "Your leave record was updated." });
      await reload();
    } catch (e) {
      notifications.show({ color: "red", title: "Could not update leave", message: errorMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  async function requestCancellation(id: number) {
    setBusy(true);
    try {
      await http.post(`/leave/applications/${id}/cancel`);
      notifications.show({
        color: "green", title: "Cancellation requested",
        message: "Your cancellation is awaiting review.",
      });
      await reload();
    } catch (e) {
      notifications.show({
        color: "red", title: "Could not request cancellation",
        message: errorMessage(e),
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <Container size="xl">
      <PageHeader
        title={showApplicationForm ? "Apply for Leave" : "My Leave"}
        subtitle="Submit a request and review your leave balance and history."
      />
      {error && <Alert color="red" mb="md">{error}</Alert>}

      {showApplicationForm && (
        <Card withBorder mb="lg" padding="lg">
          <form onSubmit={submitApplication}>
            <Stack>
              <Select
                label="Leave category" data={categories} value={category}
                onChange={setCategory} required
              />
              <Group grow align="flex-start">
                <DateInput label="Start date" value={startDate}
                  onChange={setStartDate} required />
                <DateInput label="End date" value={endDate}
                  onChange={setEndDate} required />
              </Group>
              {category === "CL" && (
                <Select
                  label="CL period" data={[
                    { value: "full", label: "Full day" },
                    { value: "first_half", label: "First half" },
                    { value: "second_half", label: "Second half" },
                  ]}
                  value={halfDay} onChange={(value) => setHalfDay(value ?? "full")}
                />
              )}
              <Textarea label="Purpose / reason" value={reason}
                onChange={(event) => setReason(event.currentTarget.value)}
                minRows={2} required />
              <TextInput label="Supporting evidence reference (if required)"
                value={evidence} onChange={(event) => setEvidence(event.currentTarget.value)} />
              <TextInput label="Substitute Fusion user ID (when required)"
                value={substituteId}
                onChange={(event) => setSubstituteId(event.currentTarget.value)} />
              <Checkbox label="I will be outside Jabalpur (Station Leave)"
                checked={stationLeave} onChange={(event) => setStationLeave(event.currentTarget.checked)} />
              {stationLeave && (
                <TextInput label="Station Leave destination" value={destination}
                  onChange={(event) => setDestination(event.currentTarget.value)} required />
              )}
              <Button type="submit" loading={busy}>Submit leave request</Button>
            </Stack>
          </form>
        </Card>
      )}

      <Card withBorder mb="lg" padding="lg">
        <Text fw={600} mb="sm">Current-year balances</Text>
        <Table.ScrollContainer minWidth={650}>
          <Table striped>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Category</Table.Th><Table.Th>Entitlement</Table.Th>
                <Table.Th>Carry-in</Table.Th><Table.Th>Converted</Table.Th>
                <Table.Th>Used</Table.Th><Table.Th>Available</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {balances.map((row) => (
                <Table.Tr key={`${row.category}-${row.year}`}>
                  <Table.Td>{row.category_label}</Table.Td>
                  <Table.Td>{row.entitlement}</Table.Td>
                  <Table.Td>{row.carried_in}</Table.Td>
                  <Table.Td>{row.converted_in}</Table.Td>
                  <Table.Td>{row.used}</Table.Td>
                  <Table.Td>{row.available}</Table.Td>
                </Table.Tr>
              ))}
              {!loading && balances.length === 0 && (
                <Table.Tr><Table.Td colSpan={6}>No balances available.</Table.Td></Table.Tr>
              )}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      </Card>

      <Card withBorder padding="lg">
        <Group justify="space-between" mb="sm">
          <Text fw={600}>Application history</Text>
          <Button variant="default" size="xs" onClick={() => void reload()} loading={loading}>
            Refresh
          </Button>
        </Group>
        <Table.ScrollContainer minWidth={780}>
          <Table striped>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Category</Table.Th><Table.Th>Period</Table.Th>
                <Table.Th>Type</Table.Th><Table.Th>Status</Table.Th>
                <Table.Th>Station Leave</Table.Th><Table.Th>Actions</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {applications.map((row) => (
                <Table.Tr key={row.id}>
                  <Table.Td>{row.category}</Table.Td>
                  <Table.Td>{row.start_date} – {row.end_date}</Table.Td>
                  <Table.Td>{row.request_type}</Table.Td>
                  <Table.Td>{row.status.replaceAll("_", " ")}</Table.Td>
                  <Table.Td>{row.station_leave ? "Yes" : "No"}</Table.Td>
                  <Table.Td>
                    <Group gap="xs">
                      <Button size="xs" variant="subtle"
                        onClick={() => setSelectedId(String(row.id))}>
                        Select
                      </Button>
                      {row.status === "approved" && (
                        <Button size="xs" variant="light" color="red"
                          loading={busy}
                          onClick={() => void requestCancellation(row.id)}>
                          Request cancellation
                        </Button>
                      )}
                      {[
                        "substitute_response", "unit_head_review",
                        "establishment_review", "final_review",
                      ].includes(row.status) && (
                        <Button size="xs" variant="subtle" color="gray"
                          loading={busy}
                          onClick={() => void submitActionFor(row.id, "withdraw")}>
                          Withdraw
                        </Button>
                      )}
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))}
              {!loading && applications.length === 0 && (
                <Table.Tr><Table.Td colSpan={6}>No leave applications yet.</Table.Td></Table.Tr>
              )}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      </Card>

      <Card withBorder mt="lg" padding="lg">
        <Text fw={600} mb="sm">Extension and resumption</Text>
        <Stack>
          <Select
            label="Approved leave"
            placeholder="Select an approved leave record"
            data={selectableApplications.map((row) => ({
              value: String(row.id),
              label: `#${row.id} ${row.category} (${row.start_date} – ${row.end_date})`,
            }))}
            value={selectedId} onChange={setSelectedId}
          />
          <Group grow align="flex-end">
            <DateInput label="Requested extension end date" value={extensionEnd}
              onChange={setExtensionEnd} />
            <Button variant="light" loading={busy}
              disabled={!selectedId || !extensionEnd}
              onClick={() => void submitAction("extend", {
              new_end_date: isoDate(extensionEnd),
              reason: "Extension requested",
              substitute_user_id: extensionSubstituteId
                ? Number(extensionSubstituteId) : null,
            })}>
            Request extension
            </Button>
          </Group>
          <TextInput label="Extension substitute Fusion user ID (when required)"
            value={extensionSubstituteId}
            onChange={(event) => setExtensionSubstituteId(event.currentTarget.value)} />
          <Group grow align="flex-end">
            <DateInput label="Actual resumption date" value={resumeDate}
              onChange={setResumeDate} />
            <TextInput label="Resumption details" value={resumeDetails}
              onChange={(event) => setResumeDetails(event.currentTarget.value)} />
            <Button variant="light" loading={busy}
              disabled={!selectedId || !resumeDate || !resumeDetails}
              onClick={() => void submitAction("resumption", {
                actual_resume_date: isoDate(resumeDate), details: resumeDetails,
              })}>
              Submit resumption
            </Button>
          </Group>
          <Text size="xs" c="dimmed">
            Availability and approval eligibility are validated by the server.
          </Text>
        </Stack>
      </Card>
    </Container>
  );
}
