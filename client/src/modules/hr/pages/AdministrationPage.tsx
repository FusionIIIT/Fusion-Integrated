import { useState } from "react";
import {
  Badge, Button, Card, Checkbox, Container, Group, Select, Stack, Table, Text,
  TextInput, Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useAppraisalWindows, useAuditEvents, usePublishNotice,
  useManagedLeaveBalances, useSaveAppraisalWindow, useSaveLeaveBalance,
  useSaveWorkflowRoute, useWorkflowRoutes,
} from "../api/hooks";
import type { LeaveType, WorkflowRoute } from "../api/types";

export default function AdministrationPage() {
  const { can } = useAuth();
  return <Container size="xl">
    <PageHeader title="HR Administration"
      subtitle="Approval configuration, appraisal windows, notices, and audit records" />
    {can("hr.workflow.manage") && <WorkflowRoutePanel />}
    {can("hr.leave_balance.manage") && <LeaveBalancePanel />}
    {can("hr.workflow.manage") && <AppraisalWindowPanel />}
    {can("hr.notification.manage") && <NoticePanel />}
    {can("hr.audit.view") && <AuditPanel />}
    {!can("hr.workflow.manage") && !can("hr.notification.manage") &&
      !can("hr.audit.view") && <Text c="dimmed">You do not have an HR administration permission.</Text>}
  </Container>;
}

function LeaveBalancePanel() {
  const { data, isPending, error } = useManagedLeaveBalances();
  const save = useSaveLeaveBalance();
  const [employeeId, setEmployeeId] = useState("");
  const [leaveType, setLeaveType] = useState<LeaveType | null>(null);
  const [days, setDays] = useState("");
  const [eligible, setEligible] = useState(true);
  if (error) return <ErrorState error={error} />;
  const types: { value: LeaveType; label: string }[] = [
    { value: "casual", label: "Casual" }, { value: "restricted", label: "Restricted" },
    { value: "medical", label: "Medical" }, { value: "earned", label: "Earned" },
    { value: "vacation", label: "Vacation" }, { value: "sabbatical", label: "Sabbatical" },
  ];
  function submit() {
    const id = Number(employeeId);
    if (!Number.isSafeInteger(id) || id < 1 || !leaveType || !days || Number(days) < 0) return;
    save.mutate({ employee_user_id: id, leave_type: leaveType,
      available_days: days, is_eligible: eligible }, {
      onSuccess: () => notifications.show({ color: "green", title: "Leave balance saved", message: "The balance change was added to its ledger." }),
      onError: (cause) => notifications.show({ color: "red", title: "Could not save leave balance", message: errorMessage(cause) }),
    });
  }
  return <Card withBorder mb="md"><Stack>
    <Text fw={700}>Employee leave balances and eligibility</Text>
    {isPending ? <Text>Loading leave balances…</Text> : data?.results.length ? (
      <Table.ScrollContainer minWidth={650}><Table striped>
        <Table.Thead><Table.Tr><Table.Th>Employee</Table.Th><Table.Th>Leave type</Table.Th>
          <Table.Th>Available days</Table.Th><Table.Th>Eligible</Table.Th></Table.Tr></Table.Thead>
        <Table.Tbody>{data.results.map((balance) => (
          <Table.Tr key={balance.id}><Table.Td>{balance.employee_user_id}</Table.Td>
            <Table.Td>{balance.leave_type_display}</Table.Td><Table.Td>{balance.available_days}</Table.Td>
            <Table.Td>{balance.is_eligible ? "Yes" : "No"}</Table.Td></Table.Tr>
        ))}</Table.Tbody>
      </Table></Table.ScrollContainer>
    ) : <Text c="dimmed">No leave balances have been configured.</Text>}
    <Group grow>
      <TextInput label="Employee user ID" type="number" min="1" value={employeeId}
        onChange={(event) => setEmployeeId(event.currentTarget.value)} />
      <Select label="Leave type" value={leaveType} onChange={(value) => setLeaveType(value as LeaveType | null)} data={types} />
      <TextInput label="Available days" type="number" min="0" step="0.01" value={days}
        onChange={(event) => setDays(event.currentTarget.value)} />
    </Group>
    <Checkbox label="Eligible for this leave type" checked={eligible} onChange={(event) => setEligible(event.currentTarget.checked)} />
    <Group justify="flex-end"><Button loading={save.isPending}
      disabled={!employeeId || !leaveType || days === "" || Number(days) < 0}
      onClick={submit}>Save balance and eligibility</Button></Group>
  </Stack></Card>;
}

function WorkflowRoutePanel() {
  const { data, isPending, error } = useWorkflowRoutes();
  const save = useSaveWorkflowRoute();
  const [category, setCategory] = useState("faculty");
  const [type, setType] = useState<WorkflowRoute["request_type"]>("ltc_advance");
  const [steps, setSteps] = useState("[]");
  const [reminder, setReminder] = useState("");
  function submit() {
    let parsed: WorkflowRoute["steps"];
    try {
      parsed = JSON.parse(steps) as WorkflowRoute["steps"];
      if (!Array.isArray(parsed) || parsed.length === 0) throw new Error("Enter a non-empty JSON array.");
    } catch (e) {
      notifications.show({ color: "red", title: "Invalid approval route", message: e instanceof Error ? e.message : errorMessage(e) });
      return;
    }
    const delay = reminder.trim() ? Number(reminder) : null;
    if (delay !== null && (!Number.isSafeInteger(delay) || delay < 1)) {
      notifications.show({ color: "red", title: "Invalid reminder delay", message: "Use a positive whole number of hours." });
      return;
    }
    save.mutate({ employee_category: category, request_type: type,
      steps: parsed, reminder_after_hours: delay }, {
      onSuccess: () => notifications.show({ color: "green", title: "Approval route saved", message: "The configuration was saved." }),
      onError: (e) => notifications.show({ color: "red", title: "Could not save route", message: errorMessage(e) }),
    });
  }
  if (error) return <ErrorState error={error} />;
  return <Card withBorder mb="md"><Stack>
        <Text fw={700}>Approval routes</Text>
    {isPending ? <Text>Loading routes…</Text> : data?.results.length ? (
      <Table.ScrollContainer minWidth={650}><Table striped>
        <Table.Thead><Table.Tr><Table.Th>Category</Table.Th><Table.Th>Request type</Table.Th>
          <Table.Th>Approvers</Table.Th><Table.Th>Reminder</Table.Th></Table.Tr></Table.Thead>
        <Table.Tbody>{data.results.map((route) => (
          <Table.Tr key={route.id}><Table.Td>{route.employee_category}</Table.Td>
            <Table.Td>{route.request_type}</Table.Td>
            <Table.Td>{route.steps.map((step) => `${step.authority_label} (${step.approver_user_id})`).join(" → ")}</Table.Td>
            <Table.Td>{route.reminder_after_hours ? `${route.reminder_after_hours} hours` : "Off"}</Table.Td>
          </Table.Tr>
        ))}</Table.Tbody>
      </Table></Table.ScrollContainer>
    ) : <Text c="dimmed">No approval routes have been configured.</Text>}
    <Group grow>
      <Select label="Employee category" value={category} onChange={(v) => v && setCategory(v)} data={["faculty", "staff"]} />
      <Select label="Request type" value={type} onChange={(v) => v && setType(v as WorkflowRoute["request_type"])}
        data={["ltc_advance", "ltc_reimbursement", "cpda_advance", "cpda_reimbursement",
          "leave_casual", "leave_restricted", "leave_medical", "leave_earned",
          "leave_vacation", "leave_sabbatical"]} />
      <TextInput label="Reminder after hours (blank disables)" type="number" min="1"
        value={reminder} onChange={(e) => setReminder(e.currentTarget.value)} />
    </Group>
    <Textarea label="Ordered approval steps (JSON array)" minRows={5}
      value={steps} onChange={(e) => setSteps(e.currentTarget.value)} />
    <Group justify="flex-end"><Button loading={save.isPending} onClick={submit}>Save route</Button></Group>
  </Stack></Card>;
}

function AppraisalWindowPanel() {
  const { data, isPending, error } = useAppraisalWindows();
  const save = useSaveAppraisalWindow();
  const [period, setPeriod] = useState("");
  const [opensAt, setOpensAt] = useState("");
  const [closesAt, setClosesAt] = useState("");
  if (error) return <ErrorState error={error} />;
  return <Card withBorder mb="md"><Stack>
    <Text fw={700}>Appraisal submission windows</Text>
    {isPending ? <Text>Loading windows…</Text> : data?.results.length ? (
      <Table><Table.Thead><Table.Tr><Table.Th>Period</Table.Th><Table.Th>Opens</Table.Th>
        <Table.Th>Closes</Table.Th><Table.Th>Status</Table.Th></Table.Tr></Table.Thead>
        <Table.Tbody>{data.results.map((window) => (
          <Table.Tr key={window.id}><Table.Td>{window.period}</Table.Td>
            <Table.Td>{new Date(window.opens_at).toLocaleString()}</Table.Td>
            <Table.Td>{new Date(window.closes_at).toLocaleString()}</Table.Td>
            <Table.Td><Badge>{window.is_active ? "Active" : "Inactive"}</Badge></Table.Td>
          </Table.Tr>
        ))}</Table.Tbody>
      </Table>
    ) : <Text c="dimmed">No appraisal windows are configured.</Text>}
    <Group grow>
      <TextInput label="Period" value={period} onChange={(e) => setPeriod(e.currentTarget.value)} />
      <TextInput type="datetime-local" label="Opens at" value={opensAt} onChange={(e) => setOpensAt(e.currentTarget.value)} />
      <TextInput type="datetime-local" label="Closes at" value={closesAt} onChange={(e) => setClosesAt(e.currentTarget.value)} />
    </Group>
    <Group justify="flex-end"><Button loading={save.isPending}
      disabled={!period.trim() || !opensAt || !closesAt}
      onClick={() => {
        const opening = new Date(opensAt);
        const closing = new Date(closesAt);
        if (Number.isNaN(opening.getTime()) || Number.isNaN(closing.getTime()) || closing <= opening) {
          notifications.show({ color: "red", title: "Invalid appraisal window", message: "The closing time must be after the opening time." });
          return;
        }
        save.mutate({ period, opens_at: opening.toISOString(),
          closes_at: closing.toISOString(), is_active: true }, {
          onSuccess: () => { notifications.show({ color: "green", title: "Window saved", message: "The appraisal window was saved." }); setPeriod(""); setOpensAt(""); setClosesAt(""); },
          onError: (e) => notifications.show({ color: "red", title: "Could not save window", message: errorMessage(e) }),
        });
      }}>Save window</Button></Group>
  </Stack></Card>;
}

function NoticePanel() {
  const publish = usePublishNotice();
  const [recipients, setRecipients] = useState("");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  function submit() {
    const ids = recipients.split(",").map((value) => Number(value.trim()));
    if (!ids.length || ids.some((id) => !Number.isSafeInteger(id) || id < 1)) {
      notifications.show({ color: "red", title: "Invalid recipients", message: "Enter employee IDs separated by commas." });
      return;
    }
    publish.mutate({ recipient_user_ids: ids, subject, body }, {
      onSuccess: (result) => {
        notifications.show({ color: "green", title: "Notice published", message: `Sent to ${result.published} employees.` });
        setRecipients(""); setSubject(""); setBody("");
      },
      onError: (e) => notifications.show({ color: "red", title: "Could not publish notice", message: errorMessage(e) }),
    });
  }
  return <Card withBorder mb="md"><Stack>
    <Text fw={700}>Publish HR notice</Text>
    <TextInput label="Recipient employee IDs" placeholder="123, 456" value={recipients}
      onChange={(e) => setRecipients(e.currentTarget.value)} />
    <TextInput label="Subject" maxLength={160} value={subject}
      onChange={(e) => setSubject(e.currentTarget.value)} />
    <Textarea label="Notice" maxLength={2000} minRows={4} value={body}
      onChange={(e) => setBody(e.currentTarget.value)} />
    <Group justify="flex-end"><Button loading={publish.isPending}
      disabled={!subject.trim() || !body.trim()} onClick={submit}>Publish notice</Button></Group>
  </Stack></Card>;
}

function AuditPanel() {
  const { data, isPending, error } = useAuditEvents();
  if (error) return <ErrorState error={error} />;
  return <Card withBorder><Stack><Text fw={700}>HR audit events</Text>
    {isPending ? <Text>Loading audit events…</Text> : data?.results.length ? (
      <Table.ScrollContainer minWidth={800}><Table striped>
        <Table.Thead><Table.Tr><Table.Th>Time</Table.Th><Table.Th>Actor</Table.Th>
          <Table.Th>Action</Table.Th><Table.Th>Entity</Table.Th></Table.Tr></Table.Thead>
        <Table.Tbody>{data.results.map((event) => (
          <Table.Tr key={event.id}><Table.Td>{new Date(event.created_at).toLocaleString()}</Table.Td>
            <Table.Td>{event.actor_user_id ?? "System"}</Table.Td><Table.Td>{event.action}</Table.Td>
            <Table.Td>{event.entity_type} #{event.entity_id}</Table.Td>
          </Table.Tr>
        ))}</Table.Tbody>
      </Table></Table.ScrollContainer>
    ) : <Text c="dimmed">No audit events have been recorded.</Text>}
  </Stack></Card>;
}
