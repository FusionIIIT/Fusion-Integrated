import { useCallback, useEffect, useState } from "react";
import { Alert, Button, Card, Container, Group, Stack, Table, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage, http } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";

type LeaveTask = {
  id: number;
  employee_id: number;
  category: string;
  request_type: string;
  status: string;
  start_date: string;
  end_date: string;
  reason: string;
  station_leave: boolean;
  station_destination: string;
};

type ResumptionTask = {
  id: number;
  application_id: number;
  actual_resume_date: string;
  details: string;
};

export default function ApprovalsPage() {
  const [tasks, setTasks] = useState<LeaveTask[]>([]);
  const [resumptions, setResumptions] = useState<ResumptionTask[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<number | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [leaveResponse, resumptionResponse] = await Promise.all([
        http.get<{ results: LeaveTask[] }>("/leave/approvals"),
        http.get<{ results: ResumptionTask[] }>("/leave/resumptions"),
      ]);
      setTasks(leaveResponse.data.results);
      setResumptions(resumptionResponse.data.results);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void reload(); }, [reload]);

  async function act(id: number, decision: string, extra: object = {}) {
    setBusy(id);
    try {
      await http.post(`/leave/applications/${id}/decision`, { decision, ...extra });
      notifications.show({ color: "green", title: "Recorded", message: "Leave task updated." });
      await reload();
    } catch (e) {
      notifications.show({ color: "red", title: "Could not update task", message: errorMessage(e) });
    } finally {
      setBusy(null);
    }
  }

  async function respondToSubstitute(id: number, accept: boolean) {
    setBusy(id);
    try {
      await http.post(`/leave/applications/${id}/substitute-response`, { accept });
      await reload();
    } catch (e) {
      notifications.show({ color: "red", title: "Could not respond", message: errorMessage(e) });
    } finally {
      setBusy(null);
    }
  }

  async function reviewResumption(id: number, decision: string) {
    setBusy(id);
    try {
      await http.post(`/leave/resumptions/${id}/decision`, { decision });
      notifications.show({ color: "green", title: "Recorded", message: "Resumption reviewed." });
      await reload();
    } catch (e) {
      notifications.show({ color: "red", title: "Could not review resumption", message: errorMessage(e) });
    } finally {
      setBusy(null);
    }
  }

  return (
    <Container size="xl">
      <PageHeader title="Leave Approval Queue"
        subtitle="Only tasks assigned to your Fusion identity are shown." />
      {error && <Alert color="red" mb="md">{error}</Alert>}
      <Card withBorder padding="lg" mb="lg">
        <Group justify="space-between" mb="sm">
          <Text fw={600}>Leave requests</Text>
          <Button size="xs" variant="default" loading={loading} onClick={() => void reload()}>
            Refresh
          </Button>
        </Group>
        <Table.ScrollContainer minWidth={900}>
          <Table striped>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Employee</Table.Th><Table.Th>Request</Table.Th>
                <Table.Th>Period</Table.Th><Table.Th>Reason / Station Leave</Table.Th>
                <Table.Th>Action</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {tasks.map((task) => (
                <Table.Tr key={task.id}>
                  <Table.Td>{task.employee_id}</Table.Td>
                  <Table.Td>{task.category} · {task.request_type}</Table.Td>
                  <Table.Td>{task.start_date} – {task.end_date}</Table.Td>
                  <Table.Td>
                    <Stack gap={2}>
                      <Text size="sm">{task.reason}</Text>
                      {task.station_leave && (
                        <Text size="xs" c="dimmed">Station: {task.station_destination}</Text>
                      )}
                    </Stack>
                  </Table.Td>
                  <Table.Td>
                    <Group gap="xs" wrap="nowrap">
                      {task.status === "substitute_response" ? (
                        <>
                          <Button size="xs" loading={busy === task.id}
                            onClick={() => void respondToSubstitute(task.id, true)}>Accept</Button>
                          <Button size="xs" color="red" variant="light"
                            loading={busy === task.id}
                            onClick={() => void respondToSubstitute(task.id, false)}>Decline</Button>
                        </>
                      ) : task.status === "establishment_review" ? (
                        <Button size="xs" loading={busy === task.id}
                          onClick={() => void act(task.id, "approve")}>Route onward</Button>
                      ) : task.status === "unit_head_review"
                        && !["CL", "RH"].includes(task.category) ? (
                        <>
                          <Button size="xs" loading={busy === task.id}
                            onClick={() => void act(task.id, "approve", {
                              recommendation: "recommended",
                            })}>Recommend</Button>
                          <Button size="xs" color="orange" variant="light"
                            loading={busy === task.id}
                            onClick={() => void act(task.id, "reject", {
                              recommendation: "not_recommended",
                            })}>Do not recommend</Button>
                        </>
                      ) : (
                        <>
                          <Button size="xs" loading={busy === task.id}
                            onClick={() => void act(task.id, "approve")}>Approve</Button>
                          <Button size="xs" color="red" variant="light"
                            loading={busy === task.id}
                            onClick={() => void act(task.id, "reject")}>Reject</Button>
                        </>
                      )}
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))}
              {!loading && tasks.length === 0 && (
                <Table.Tr><Table.Td colSpan={5}>No assigned requests.</Table.Td></Table.Tr>
              )}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      </Card>

      <Card withBorder padding="lg">
        <Text fw={600} mb="sm">Resumption reviews</Text>
        <Table>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Leave record</Table.Th><Table.Th>Actual return</Table.Th>
              <Table.Th>Details</Table.Th><Table.Th>Action</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {resumptions.map((row) => (
              <Table.Tr key={row.id}>
                <Table.Td>#{row.application_id}</Table.Td>
                <Table.Td>{row.actual_resume_date}</Table.Td>
                <Table.Td>{row.details}</Table.Td>
                <Table.Td>
                  <Group gap="xs">
                    <Button size="xs" loading={busy === row.id}
                      onClick={() => void reviewResumption(row.id, "approve")}>Approve</Button>
                    <Button size="xs" color="red" variant="light" loading={busy === row.id}
                      onClick={() => void reviewResumption(row.id, "reject")}>Reject</Button>
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
            {!loading && resumptions.length === 0 && (
              <Table.Tr><Table.Td colSpan={4}>No pending resumption reviews.</Table.Td></Table.Tr>
            )}
          </Table.Tbody>
        </Table>
      </Card>
    </Container>
  );
}
