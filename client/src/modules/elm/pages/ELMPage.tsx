import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Textarea,
  Title,
} from "@mantine/core";
import { DateInput, type DateValue } from "@mantine/dates";
import { notifications } from "@mantine/notifications";
import { http, errorMessage } from "../../../lib/http";

type LeaveRow = {
  id: number;
  user_id: number;
  category: string;
  start_date: string;
  end_date: string;
  part_of_day: string;
  days_requested: string;
  reason: string;
  status: string;
  current_stage: string;
  substitute_user_id: number | null;
  substitute_status: string;
  station_leave: boolean;
  station_destination: string;
  resumption_date: string | null;
  resumption_status: string;
};

type BalanceRow = {
  id: number;
  year: number;
  category: string;
  entitled_days: string;
  used_days: string;
  carried_forward_days: string;
  available_days: string;
};

type Props = {
  view: "requests" | "balances" | "queue" | "substitute" | "admin";
};

const formatDate = (d: Date | null): string | null => {
  if (!d) return null;
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

export default function ELMPage({ view }: Props) {
  const qc = useQueryClient();

  // Application state
  const [category, setCategory] = useState<string | null>("CL");
  const [startDate, setStartDate] = useState<DateValue>(null);
  const [endDate, setEndDate] = useState<DateValue>(null);
  const [partOfDay, setPartOfDay] = useState<string | null>("full");
  const [reason, setReason] = useState("");
  const [station, setStation] = useState(false);
  const [destination, setDestination] = useState("");
  const [substituteId, setSubstituteId] = useState("");

  // Modals & action states
  const [activeReqId, setActiveReqId] = useState<number | null>(null);
  const [cancelModalOpen, setCancelModalOpen] = useState(false);
  const [cancelReason, setCancelReason] = useState("");
  const [resumeModalOpen, setResumeModalOpen] = useState(false);
  const [resumeDate, setResumeDate] = useState<DateValue>(null);
  const [extendModalOpen, setExtendModalOpen] = useState(false);
  const [extendEndDate, setExtendEndDate] = useState<DateValue>(null);
  const [extendReason, setExtendReason] = useState("");
  const [decisionNote, setDecisionNote] = useState("");

  // Offline admin state
  const [offlineUserId, setOfflineUserId] = useState("");
  const [offlineCategory, setOfflineCategory] = useState<string | null>("CL");
  const [offlineStart, setOfflineStart] = useState<DateValue>(null);
  const [offlineEnd, setOfflineEnd] = useState<DateValue>(null);
  const [offlineDays, setOfflineDays] = useState("1");
  const [offlineRef, setOfflineRef] = useState("");
  const [offlineReason, setOfflineReason] = useState("");

  const url =
    view === "balances"
      ? "/elm/balances"
      : view === "queue"
      ? "/elm/requests/queue"
      : view === "substitute"
      ? "/elm/substitute/queue"
      : "/elm/requests";

  const query = useQuery({
    queryKey: ["elm", view],
    queryFn: async () => (await http.get(url)).data,
  });

  // Submit leave request
  const submitRequest = useMutation({
    mutationFn: async () => {
      const s = formatDate(startDate);
      const e = formatDate(endDate);
      if (!category || !s || !e) throw new Error("Select category and date interval.");
      return http.post("/elm/requests", {
        category,
        start_date: s,
        end_date: e,
        part_of_day: partOfDay,
        reason,
        station_leave: station,
        station_destination: destination,
        substitute_user_id: substituteId ? Number(substituteId) : null,
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["elm"] });
      setReason("");
      setDestination("");
      setSubstituteId("");
      setStartDate(null);
      setEndDate(null);
      notifications.show({ title: "Request Submitted", message: "Your leave request has been submitted." });
    },
    onError: (err) => notifications.show({ color: "red", title: "Submission Failed", message: errorMessage(err) }),
  });

  // Withdraw
  const withdraw = useMutation({
    mutationFn: async (id: number) => http.post(`/elm/requests/${id}/withdraw`, {}),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["elm"] });
      notifications.show({ title: "Request Withdrawn", message: "Leave request has been withdrawn." });
    },
    onError: (err) => notifications.show({ color: "red", title: "Error", message: errorMessage(err) }),
  });

  // Cancel approved leave
  const cancel = useMutation({
    mutationFn: async () => {
      if (!activeReqId) return;
      return http.post(`/elm/requests/${activeReqId}/cancel`, { reason: cancelReason });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["elm"] });
      setCancelModalOpen(false);
      setCancelReason("");
      notifications.show({ title: "Leave Cancelled", message: "Approved leave cancelled and balance restored." });
    },
    onError: (err) => notifications.show({ color: "red", title: "Error", message: errorMessage(err) }),
  });

  // Resumption
  const resume = useMutation({
    mutationFn: async () => {
      if (!activeReqId) return;
      const rDate = formatDate(resumeDate);
      if (!rDate) throw new Error("Select actual return date.");
      return http.post(`/elm/requests/${activeReqId}/resume`, { resumption_date: rDate });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["elm"] });
      setResumeModalOpen(false);
      setResumeDate(null);
      notifications.show({ title: "Resumption Recorded", message: "Duty resumption processed." });
    },
    onError: (err) => notifications.show({ color: "red", title: "Error", message: errorMessage(err) }),
  });

  // Extension
  const extend = useMutation({
    mutationFn: async () => {
      if (!activeReqId) return;
      const eDate = formatDate(extendEndDate);
      if (!eDate) throw new Error("Select new extension end date.");
      return http.post(`/elm/requests/${activeReqId}/extend`, {
        extension_end_date: eDate,
        reason: extendReason,
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["elm"] });
      setExtendModalOpen(false);
      setExtendEndDate(null);
      setExtendReason("");
      notifications.show({ title: "Extension Submitted", message: "Leave extension request submitted." });
    },
    onError: (err) => notifications.show({ color: "red", title: "Error", message: errorMessage(err) }),
  });

  // Substitute response
  const respondSubstitute = useMutation({
    mutationFn: async ({ id, decision }: { id: number; decision: "accept" | "decline" }) =>
      http.post(`/elm/substitute/${id}/respond`, { decision }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["elm"] });
      notifications.show({ title: "Response Recorded", message: "Substitute response updated." });
    },
    onError: (err) => notifications.show({ color: "red", title: "Error", message: errorMessage(err) }),
  });

  // Review decision
  const decide = useMutation({
    mutationFn: async ({ id, decision }: { id: number; decision: string }) =>
      http.post(`/elm/requests/${id}/decision`, { decision, note: decisionNote }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["elm"] });
      setDecisionNote("");
      notifications.show({ title: "Decision Recorded", message: "Review decision updated." });
    },
    onError: (err) => notifications.show({ color: "red", title: "Error", message: errorMessage(err) }),
  });

  // Offline entry submit
  const submitOffline = useMutation({
    mutationFn: async () => {
      const s = formatDate(offlineStart);
      const e = formatDate(offlineEnd);
      if (!offlineCategory || !s || !e || !offlineUserId || !offlineRef) {
        throw new Error("Complete all required fields.");
      }
      return http.post("/elm/admin/offline-entry", {
        user_id: Number(offlineUserId),
        category: offlineCategory,
        start_date: s,
        end_date: e,
        days_requested: Number(offlineDays),
        offline_reference: offlineRef,
        reason: offlineReason,
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["elm"] });
      setOfflineUserId("");
      setOfflineRef("");
      setOfflineReason("");
      setOfflineStart(null);
      setOfflineEnd(null);
      notifications.show({ title: "Offline Entry Recorded", message: "Sanction record synchronized." });
    },
    onError: (err) => notifications.show({ color: "red", title: "Error", message: errorMessage(err) }),
  });

  const getStatusBadge = (statusStr: string) => {
    const map: Record<string, string> = {
      approved: "green",
      pending: "yellow",
      rejected: "red",
      withdrawn: "gray",
      cancelled: "orange",
    };
    return <Badge color={map[statusStr] || "blue"}>{statusStr.toUpperCase()}</Badge>;
  };

  const title =
    view === "balances"
      ? "My Leave Balances"
      : view === "queue"
      ? "Leave Approval Queue"
      : view === "substitute"
      ? "Substitute Responsibilities"
      : view === "admin"
      ? "Leave Administration"
      : "Employee Leave Management";

  const rows: any[] = query.data ?? [];

  return (
    <Container size="xl" py="lg">
      <Stack gap="lg">
        <Title order={2}>{title}</Title>
        {query.error && <Text c="red">{errorMessage(query.error)}</Text>}

        {/* View 1: Requests & Application Form */}
        {view === "requests" && (
          <>
            <Card withBorder padding="md">
              <Stack gap="sm">
                <Title order={4}>Apply for Leave</Title>
                <Group grow>
                  <Select
                    label="Leave Category"
                    data={["CL", "RH", "SCL", "EL", "COL", "VL"]}
                    value={category}
                    onChange={setCategory}
                  />
                  {category === "CL" && (
                    <Select
                      label="Day Part"
                      data={[
                        { value: "full", label: "Full Day" },
                        { value: "first_half", label: "First Half (0.5)" },
                        { value: "second_half", label: "Second Half (0.5)" },
                      ]}
                      value={partOfDay}
                      onChange={setPartOfDay}
                    />
                  )}
                  <TextInput
                    label="Substitute Employee ID (Optional)"
                    placeholder="e.g. 102"
                    value={substituteId}
                    onChange={(e) => setSubstituteId(e.currentTarget.value)}
                  />
                </Group>
                <Group grow>
                  <DateInput
                    label="Start Date"
                    placeholder="YYYY-MM-DD"
                    value={startDate}
                    onChange={setStartDate}
                  />
                  <DateInput
                    label="End Date"
                    placeholder="YYYY-MM-DD"
                    value={endDate}
                    onChange={setEndDate}
                  />
                </Group>
                <Textarea
                  label="Purpose / Reason"
                  placeholder="State the reason for leave"
                  value={reason}
                  onChange={(e) => setReason(e.currentTarget.value)}
                />
                <Group grow>
                  <Select
                    label="Station Leave"
                    data={[
                      { value: "no", label: "No (Within Jabalpur)" },
                      { value: "yes", label: "Yes (Leaving Jabalpur)" },
                    ]}
                    value={station ? "yes" : "no"}
                    onChange={(v) => setStation(v === "yes")}
                  />
                  {station && (
                    <TextInput
                      label="Station Destination"
                      placeholder="e.g. New Delhi"
                      value={destination}
                      onChange={(e) => setDestination(e.currentTarget.value)}
                    />
                  )}
                </Group>
                <Button loading={submitRequest.isPending} onClick={() => submitRequest.mutate()}>
                  Submit Application
                </Button>
              </Stack>
            </Card>

            <Card withBorder padding="md">
              <Title order={4} mb="sm">My Leave History</Title>
              <Table.ScrollContainer minWidth={700}>
                <Table striped highlightOnHover>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>ID</Table.Th>
                      <Table.Th>Category</Table.Th>
                      <Table.Th>Dates</Table.Th>
                      <Table.Th>Days</Table.Th>
                      <Table.Th>Status</Table.Th>
                      <Table.Th>Stage</Table.Th>
                      <Table.Th>Substitute</Table.Th>
                      <Table.Th>Actions</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {rows.map((r: LeaveRow) => (
                      <Table.Tr key={r.id}>
                        <Table.Td>#{r.id}</Table.Td>
                        <Table.Td><Badge variant="outline">{r.category}</Badge></Table.Td>
                        <Table.Td>{r.start_date} to {r.end_date}</Table.Td>
                        <Table.Td>{r.days_requested}</Table.Td>
                        <Table.Td>{getStatusBadge(r.status)}</Table.Td>
                        <Table.Td><Text size="xs">{r.current_stage}</Text></Table.Td>
                        <Table.Td><Text size="xs">{r.substitute_status}</Text></Table.Td>
                        <Table.Td>
                          <Group gap="xs">
                            {r.status === "pending" && (
                              <Button
                                size="xs"
                                color="red"
                                variant="subtle"
                                onClick={() => withdraw.mutate(r.id)}
                              >
                                Withdraw
                              </Button>
                            )}
                            {r.status === "approved" && (
                              <>
                                <Button
                                  size="xs"
                                  color="orange"
                                  variant="subtle"
                                  onClick={() => {
                                    setActiveReqId(r.id);
                                    setCancelModalOpen(true);
                                  }}
                                >
                                  Cancel
                                </Button>
                                {["EL", "COL", "VL"].includes(r.category) && (
                                  <>
                                    <Button
                                      size="xs"
                                      color="blue"
                                      variant="subtle"
                                      onClick={() => {
                                        setActiveReqId(r.id);
                                        setExtendModalOpen(true);
                                      }}
                                    >
                                      Extend
                                    </Button>
                                    <Button
                                      size="xs"
                                      color="teal"
                                      variant="subtle"
                                      onClick={() => {
                                        setActiveReqId(r.id);
                                        setResumeModalOpen(true);
                                      }}
                                    >
                                      Resume
                                    </Button>
                                  </>
                                )}
                              </>
                            )}
                          </Group>
                        </Table.Td>
                      </Table.Tr>
                    ))}
                    {rows.length === 0 && (
                      <Table.Tr>
                        <Table.Td colSpan={8} align="center">No leave requests found.</Table.Td>
                      </Table.Tr>
                    )}
                  </Table.Tbody>
                </Table>
              </Table.ScrollContainer>
            </Card>
          </>
        )}

        {/* View 2: Balances */}
        {view === "balances" && (
          <Card withBorder padding="md">
            <Table.ScrollContainer minWidth={600}>
              <Table striped highlightOnHover>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Year</Table.Th>
                    <Table.Th>Category</Table.Th>
                    <Table.Th>Entitled</Table.Th>
                    <Table.Th>Carried Forward</Table.Th>
                    <Table.Th>Used</Table.Th>
                    <Table.Th>Available</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {rows.map((b: BalanceRow) => (
                    <Table.Tr key={b.id}>
                      <Table.Td>{b.year}</Table.Td>
                      <Table.Td><Badge variant="outline">{b.category}</Badge></Table.Td>
                      <Table.Td>{b.entitled_days}</Table.Td>
                      <Table.Td>{b.carried_forward_days}</Table.Td>
                      <Table.Td>{b.used_days}</Table.Td>
                      <Table.Td>
                        <Text fw={700} c={Number(b.available_days) > 0 ? "teal" : "red"}>
                          {b.available_days}
                        </Text>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                  {rows.length === 0 && (
                    <Table.Tr>
                      <Table.Td colSpan={6} align="center">No balances found.</Table.Td>
                    </Table.Tr>
                  )}
                </Table.Tbody>
              </Table>
            </Table.ScrollContainer>
          </Card>
        )}

        {/* View 3: Substitute Responsibilities */}
        {view === "substitute" && (
          <Card withBorder padding="md">
            <Table.ScrollContainer minWidth={600}>
              <Table striped highlightOnHover>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>ID</Table.Th>
                    <Table.Th>Applicant ID</Table.Th>
                    <Table.Th>Category</Table.Th>
                    <Table.Th>Period</Table.Th>
                    <Table.Th>Reason</Table.Th>
                    <Table.Th>Actions</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {rows.map((r: LeaveRow) => (
                    <Table.Tr key={r.id}>
                      <Table.Td>#{r.id}</Table.Td>
                      <Table.Td>User #{r.user_id}</Table.Td>
                      <Table.Td><Badge>{r.category}</Badge></Table.Td>
                      <Table.Td>{r.start_date} to {r.end_date}</Table.Td>
                      <Table.Td>{r.reason}</Table.Td>
                      <Table.Td>
                        <Group gap="xs">
                          <Button
                            size="xs"
                            color="green"
                            onClick={() => respondSubstitute.mutate({ id: r.id, decision: "accept" })}
                          >
                            Accept
                          </Button>
                          <Button
                            size="xs"
                            color="red"
                            variant="outline"
                            onClick={() => respondSubstitute.mutate({ id: r.id, decision: "decline" })}
                          >
                            Decline
                          </Button>
                        </Group>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                  {rows.length === 0 && (
                    <Table.Tr>
                      <Table.Td colSpan={6} align="center">No pending substitute requests.</Table.Td>
                    </Table.Tr>
                  )}
                </Table.Tbody>
              </Table>
            </Table.ScrollContainer>
          </Card>
        )}

        {/* View 4: Approval Queue */}
        {view === "queue" && (
          <Stack gap="md">
            <TextInput
              label="Review Note / Remark"
              placeholder="e.g. Recommended for academic sanction"
              value={decisionNote}
              onChange={(e) => setDecisionNote(e.currentTarget.value)}
            />
            <Card withBorder padding="md">
              <Table.ScrollContainer minWidth={700}>
                <Table striped highlightOnHover>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>ID</Table.Th>
                      <Table.Th>Applicant</Table.Th>
                      <Table.Th>Category</Table.Th>
                      <Table.Th>Period</Table.Th>
                      <Table.Th>Days</Table.Th>
                      <Table.Th>Stage</Table.Th>
                      <Table.Th>Reason</Table.Th>
                      <Table.Th>Actions</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {rows.map((r: LeaveRow) => (
                      <Table.Tr key={r.id}>
                        <Table.Td>#{r.id}</Table.Td>
                        <Table.Td>User #{r.user_id}</Table.Td>
                        <Table.Td><Badge>{r.category}</Badge></Table.Td>
                        <Table.Td>{r.start_date} to {r.end_date}</Table.Td>
                        <Table.Td>{r.days_requested}</Table.Td>
                        <Table.Td><Badge variant="dot">{r.current_stage}</Badge></Table.Td>
                        <Table.Td>{r.reason}</Table.Td>
                        <Table.Td>
                          <Group gap="xs">
                            {["CL", "RH"].includes(r.category) ? (
                              <>
                                <Button
                                  size="xs"
                                  color="green"
                                  onClick={() => decide.mutate({ id: r.id, decision: "approve" })}
                                >
                                  Approve
                                </Button>
                                <Button
                                  size="xs"
                                  color="red"
                                  variant="outline"
                                  onClick={() => decide.mutate({ id: r.id, decision: "reject" })}
                                >
                                  Reject
                                </Button>
                              </>
                            ) : (
                              <>
                                <Button
                                  size="xs"
                                  color="blue"
                                  onClick={() => decide.mutate({ id: r.id, decision: "recommend" })}
                                >
                                  Recommend
                                </Button>
                                <Button
                                  size="xs"
                                  color="orange"
                                  variant="outline"
                                  onClick={() => decide.mutate({ id: r.id, decision: "not_recommend" })}
                                >
                                  Not Recommend
                                </Button>
                                <Button
                                  size="xs"
                                  color="green"
                                  onClick={() => decide.mutate({ id: r.id, decision: "approve" })}
                                >
                                  Sanction
                                </Button>
                              </>
                            )}
                          </Group>
                        </Table.Td>
                      </Table.Tr>
                    ))}
                    {rows.length === 0 && (
                      <Table.Tr>
                        <Table.Td colSpan={8} align="center">No requests in approval queue.</Table.Td>
                      </Table.Tr>
                    )}
                  </Table.Tbody>
                </Table>
              </Table.ScrollContainer>
            </Card>
          </Stack>
        )}

        {/* View 5: Offline Leave Administration */}
        {view === "admin" && (
          <Card withBorder padding="md">
            <Stack gap="sm">
              <Title order={4}>Record Offline-Sanctioned Leave</Title>
              <Group grow>
                <TextInput
                  label="Employee User ID"
                  placeholder="e.g. 101"
                  value={offlineUserId}
                  onChange={(e) => setOfflineUserId(e.currentTarget.value)}
                />
                <Select
                  label="Category"
                  data={["CL", "RH", "SCL", "EL", "COL", "VL"]}
                  value={offlineCategory}
                  onChange={setOfflineCategory}
                />
                <TextInput
                  label="Days Deducted"
                  value={offlineDays}
                  onChange={(e) => setOfflineDays(e.currentTarget.value)}
                />
              </Group>
              <Group grow>
                <DateInput
                  label="Sanction Start Date"
                  value={offlineStart}
                  onChange={setOfflineStart}
                />
                <DateInput
                  label="Sanction End Date"
                  value={offlineEnd}
                  onChange={setOfflineEnd}
                />
              </Group>
              <TextInput
                label="Sanction / Order Reference"
                placeholder="e.g. DIR/OFF/2026/042"
                value={offlineRef}
                onChange={(e) => setOfflineRef(e.currentTarget.value)}
              />
              <Textarea
                label="Remark"
                value={offlineReason}
                onChange={(e) => setOfflineReason(e.currentTarget.value)}
              />
              <Button loading={submitOffline.isPending} onClick={() => submitOffline.mutate()}>
                Synchronize Offline Leave
              </Button>
            </Stack>
          </Card>
        )}
      </Stack>

      {/* Cancellation Modal */}
      <Modal opened={cancelModalOpen} onClose={() => setCancelModalOpen(false)} title="Request Pre-Start Cancellation">
        <Stack gap="sm">
          <Text size="sm">Cancellation restores the deducted balance for this approved leave.</Text>
          <Textarea
            label="Reason for cancellation"
            placeholder="e.g. Scheduled travel postponed"
            value={cancelReason}
            onChange={(e) => setCancelReason(e.currentTarget.value)}
          />
          <Button color="orange" loading={cancel.isPending} onClick={() => cancel.mutate()}>
            Confirm Cancellation
          </Button>
        </Stack>
      </Modal>

      {/* Resumption Modal */}
      <Modal opened={resumeModalOpen} onClose={() => setResumeModalOpen(false)} title="Submit Resumption of Duty">
        <Stack gap="sm">
          <Text size="sm">Report the actual date of duty resumption. Early or late returns adjust leave balances accordingly.</Text>
          <DateInput
            label="Actual Resumption Date"
            placeholder="YYYY-MM-DD"
            value={resumeDate}
            onChange={setResumeDate}
          />
          <Button color="teal" loading={resume.isPending} onClick={() => resume.mutate()}>
            Submit Resumption Report
          </Button>
        </Stack>
      </Modal>

      {/* Extension Modal */}
      <Modal opened={extendModalOpen} onClose={() => setExtendModalOpen(false)} title="Request Leave Extension">
        <Stack gap="sm">
          <Text size="sm">Request additional leave days for ongoing EL/COL/VL.</Text>
          <DateInput
            label="New Extension End Date"
            placeholder="YYYY-MM-DD"
            value={extendEndDate}
            onChange={setExtendEndDate}
          />
          <Textarea
            label="Reason for extension"
            value={extendReason}
            onChange={(e) => setExtendReason(e.currentTarget.value)}
          />
          <Button color="blue" loading={extend.isPending} onClick={() => extend.mutate()}>
            Submit Extension Request
          </Button>
        </Stack>
      </Modal>
    </Container>
  );
}
