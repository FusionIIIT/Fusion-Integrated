import { useState } from "react";
import {
  Alert, Badge, Button, Container, Group, NumberInput, Select, Stack, Table,
  Text, TextInput, Title,
} from "@mantine/core";
import { DateInput } from "@mantine/dates";
import { notifications } from "@mantine/notifications";
import { FaCalendarPlus, FaTimes } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { formatLocalDate } from "../utils/dates";
import {
  useAcknowledgeTaskNotice, useLeaveAction, useLeaveRequests,
  usePrintLeaveRequest, useSubmitExtension, useSubmitLeave, useTaskNotices,
} from "../api/hooks";

const leaveTypes = ["CL", "RH", "SCL", "EL", "VL", "COL"];
const label = (status: string) => status.replaceAll("_", " ");

export default function MyLeavePage() {
  const requests = useLeaveRequests();
  const notices = useTaskNotices();
  const acknowledge = useAcknowledgeTaskNotice();
  const submit = useSubmitLeave();
  const action = useLeaveAction();
  const printable = usePrintLeaveRequest();
  const extension = useSubmitExtension();
  const [type, setType] = useState<string | null>("CL");
  const [start, setStart] = useState<Date | null>(null);
  const [end, setEnd] = useState<Date | null>(null);
  const [reason, setReason] = useState("");
  const [substitute, setSubstitute] = useState("");
  const [year, setYear] = useState<number | "">(new Date().getFullYear());
  const [extensionId, setExtensionId] = useState<number | null>(null);
  const [extensionStart, setExtensionStart] = useState<Date | null>(null);
  const [extensionEnd, setExtensionEnd] = useState<Date | null>(null);
  const [extensionReason, setExtensionReason] = useState("");
  const [resumptionId, setResumptionId] = useState<number | null>(null);
  const [resumptionDate, setResumptionDate] = useState<Date | null>(null);

  if (requests.error) return <Container size="xl"><ErrorState error={requests.error} /></Container>;

  function submitRequest() {
    if (!type || !start || !end) return;
    submit.mutate({
      leave_type: type, start_date: formatLocalDate(start),
      end_date: formatLocalDate(end), reason,
      leave_year: year || new Date().getFullYear(),
      ...(substitute ? { substitute_id: Number(substitute) } : {}),
    }, {
      onSuccess: () => {
        setReason(""); setStart(null); setEnd(null); setSubstitute("");
        notifications.show({ color: "green", message: "Leave request submitted." });
      },
      onError: (error) => notifications.show({ color: "red", message: errorMessage(error) }),
    });
  }

  function runAction(id: number, actionName: string, extra: Record<string, unknown> = {}) {
    action.mutate({ id, action: actionName, ...extra }, {
      onError: (error) => notifications.show({ color: "red", message: errorMessage(error) }),
    });
  }

  return (
    <Container size="xl">
      <PageHeader title="My Leave" subtitle="Requests, decisions and upcoming leave" />
      <Stack gap="lg">
        {notices.data?.filter((notice) => !notice.read_at).map((notice) => (
          <Alert key={notice.id} title={notice.event === "decision" ? "Leave request update" :
            notice.event === "reminder" ? "Pending task reminder" :
              notice.event === "escalated" ? "Task escalated" : "New task assigned"}
            color={notice.event === "decision" ? "green" : "blue"}>
            <Group justify="space-between" align="center">
              <Text size="sm">{notice.message}</Text>
              <Button size="xs" variant="subtle" loading={acknowledge.isPending}
                onClick={() => acknowledge.mutate(notice.id, {
                  onError: (error) => notifications.show({
                    color: "red", message: errorMessage(error),
                  }),
                })}>Mark read</Button>
            </Group>
          </Alert>
        ))}
        <section>
          <Title order={4} mb="sm">New request</Title>
          <Group align="end" grow wrap="wrap">
            <Select label="Leave category" data={leaveTypes} value={type} onChange={setType} />
            <DateInput label="From" value={start} onChange={setStart} valueFormat="DD MMM YYYY" />
            <DateInput label="Through" value={end} onChange={setEnd} valueFormat="DD MMM YYYY" />
            <NumberInput label="Leave year" min={2000} max={2200} value={year}
              onChange={(value) => setYear(typeof value === "number" ? value : "")} />
          </Group>
          <Group align="end" grow mt="sm" wrap="wrap">
            <TextInput label="Reason" value={reason} onChange={(event) => setReason(event.currentTarget.value)} />
            <TextInput label="Substitute employee ID, if required" value={substitute}
              onChange={(event) => setSubstitute(event.currentTarget.value)} />
            <Button leftSection={<FaCalendarPlus />} loading={submit.isPending}
              disabled={!type || !start || !end || !reason.trim()} onClick={submitRequest}>
              Submit request
            </Button>
          </Group>
          <Text size="xs" c="dimmed" mt="xs">Submitted requests cannot be edited. Withdraw while pending and submit a corrected request.</Text>
        </section>
        <section>
          <Title order={4} mb="sm">Request history</Title>
          {requests.isPending ? <Text c="dimmed">Loading requests…</Text> :
            requests.data?.length ? (
              <Table.ScrollContainer minWidth={760}>
                <Table striped highlightOnHover>
                  <Table.Thead><Table.Tr><Table.Th>Type</Table.Th><Table.Th>Dates</Table.Th>
                    <Table.Th>Days</Table.Th><Table.Th>Status</Table.Th><Table.Th>Reason</Table.Th>
                    <Table.Th /></Table.Tr></Table.Thead>
                  <Table.Tbody>{requests.data.map((row) => (
                    <Table.Tr key={row.id}>
                      <Table.Td>{row.leave_type}{row.request_kind !== "new" ? ` · ${row.request_kind}` : ""}</Table.Td>
                      <Table.Td>{row.start_date} – {row.end_date}</Table.Td>
                      <Table.Td>{row.charged_days}</Table.Td>
                      <Table.Td><Badge variant="light" tt="capitalize">{label(row.status)}</Badge></Table.Td>
                      <Table.Td><Text size="sm" lineClamp={1}>{row.reason}</Text></Table.Td>
                      <Table.Td><Group gap={4} wrap="wrap">
                        <Button size="xs" variant="subtle" loading={printable.isPending}
                          onClick={() => printable.mutate(row.id, {
                            onSuccess: (html) => {
                              const printWindow = window.open("", "_blank");
                              if (!printWindow) {
                                notifications.show({ color: "red", message: "Allow pop-ups to print this request." });
                                return;
                              }
                              printWindow.document.write(html);
                              printWindow.document.close();
                              printWindow.focus();
                              printWindow.print();
                            },
                            onError: (error) => notifications.show({ color: "red", message: errorMessage(error) }),
                          })}>Print</Button>
                        {["substitute_pending", "substitute_declined", "unit_head_pending",
                          "establishment_pending", "final_pending"].includes(row.status) &&
                          <Button size="xs" variant="subtle" color="red" leftSection={<FaTimes />}
                            onClick={() => runAction(row.id, "withdraw")}>Withdraw</Button>}
                        {row.status === "approved" && <>
                          <Button size="xs" variant="light" color="red"
                            onClick={() => runAction(row.id, "request_cancellation")}>Request cancellation</Button>
                          {["EL", "COL", "VL"].includes(row.leave_type) && <>
                            <Button size="xs" variant="light" onClick={() => setExtensionId(row.id)}>Extend</Button>
                            <Button size="xs" variant="light" onClick={() => setResumptionId(row.id)}>Record return</Button>
                          </>}
                        </>}</Group></Table.Td>
                    </Table.Tr>
                  ))}</Table.Tbody>
                </Table>
              </Table.ScrollContainer>
            ) : <Alert color="gray">No leave requests yet.</Alert>}
        </section>
        {extensionId !== null && <section>
          <Title order={5} mb="sm">Request an extension</Title>
          <Group align="end" grow wrap="wrap">
            <DateInput label="Extension from" value={extensionStart} onChange={setExtensionStart} />
            <DateInput label="Through" value={extensionEnd} onChange={setExtensionEnd} />
            <TextInput label="Reason" value={extensionReason}
              onChange={(event) => setExtensionReason(event.currentTarget.value)} />
            <Button loading={extension.isPending} disabled={!extensionStart || !extensionEnd || !extensionReason.trim()}
              onClick={() => extension.mutate({
                id: extensionId, start_date: extensionStart && formatLocalDate(extensionStart),
                end_date: extensionEnd && formatLocalDate(extensionEnd), reason: extensionReason,
              }, { onSuccess: () => { setExtensionId(null); setExtensionStart(null); setExtensionEnd(null); setExtensionReason(""); },
                onError: (error) => notifications.show({ color: "red", message: errorMessage(error) }) })}>
              Submit extension
            </Button>
            <Button variant="default" onClick={() => setExtensionId(null)}>Close</Button>
          </Group>
        </section>}
        {resumptionId !== null && <section>
          <Title order={5} mb="sm">Submit resumption of duty</Title>
          <Group align="end" grow wrap="wrap">
            <DateInput label="Actual return date" value={resumptionDate} onChange={setResumptionDate} />
            <Button disabled={!resumptionDate} loading={action.isPending}
              onClick={() => runAction(resumptionId, "request_resumption", {
                actual_resume_date: resumptionDate && formatLocalDate(resumptionDate),
              })}>Submit return</Button>
            <Button variant="default" onClick={() => setResumptionId(null)}>Close</Button>
          </Group>
        </section>}
      </Stack>
    </Container>
  );
}