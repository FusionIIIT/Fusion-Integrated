import { useState } from "react";
import {
  Badge, Button, Card, Container, Group, Modal, Select, Stack, Table,
  Text, TextInput, Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useCreateEmployee, useEmployees, useUpdateEmployeeRecord,
} from "../api/hooks";
import type { EmployeeRecord } from "../api/types";

export default function RecordsPage() {
  const { can } = useAuth();
  const { data, isPending, error } = useEmployees();
  const [editing, setEditing] = useState<EmployeeRecord | null | undefined>();
  const [viewing, setViewing] = useState<EmployeeRecord | null>(null);
  const canEdit = can("hr.employee.create") || can("hr.employee.update");
  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;
  return (
    <Container size="xl">
      <PageHeader title={can("hr.employee.view") ? "Employee Service Records" : "My Service Record"}
        subtitle="HR-maintained service and appointment information"
        action={can("hr.employee.create") && <Button onClick={() => setEditing(null)}>Add employee record</Button>} />
      <Card withBorder>
        {isPending ? <Text>Loading service records…</Text> : data?.results.length ? (
          <Table.ScrollContainer minWidth={900}><Table striped highlightOnHover>
            <Table.Thead><Table.Tr>
              <Table.Th>Employee ID</Table.Th><Table.Th>Category</Table.Th>
              <Table.Th>Department</Table.Th><Table.Th>Designation</Table.Th>
              <Table.Th>Status</Table.Th><Table.Th>Appointment</Table.Th>
              <Table.Th>Details</Table.Th>
              {can("hr.employee.update") && <Table.Th>Actions</Table.Th>}
            </Table.Tr></Table.Thead>
            <Table.Tbody>{data.results.map((record) => (
              <Table.Tr key={record.user_id}>
                <Table.Td>{record.user_id}</Table.Td><Table.Td>{record.employee_category}</Table.Td>
                <Table.Td>{record.department}</Table.Td><Table.Td>{record.designation}</Table.Td>
                <Table.Td><Badge>{record.employment_status}</Badge></Table.Td>
                <Table.Td>{record.appointment_type || "—"}</Table.Td>
                <Table.Td>
                  <Button size="xs" variant="subtle"
                    aria-label={`View service record details for employee ${record.user_id}`}
                    onClick={() => setViewing(record)}>Details</Button>
                </Table.Td>
                {can("hr.employee.update") && <Table.Td>
                  <Button size="xs" variant="light" onClick={() => setEditing(record)}>Edit</Button>
                </Table.Td>}
              </Table.Tr>
            ))}</Table.Tbody>
          </Table></Table.ScrollContainer>
        ) : <Text c="dimmed">No service records are available.</Text>}
      </Card>
      {canEdit && editing !== undefined && (
        <EmployeeEditor key={editing?.user_id ?? "new"} record={editing}
          onClose={() => setEditing(undefined)} />
      )}
      {viewing && <RecordDetails record={viewing} onClose={() => setViewing(null)} />}
    </Container>
  );
}

function RecordDetails({ record, onClose }: {
  record: EmployeeRecord; onClose: () => void;
}) {
  return <Modal opened onClose={onClose}
    title={`Employee ${record.user_id} service record details`} size="lg">
    <Stack>
      <Text fw={600}>Appointment details</Text>
      <Text component="pre" size="sm" style={{ whiteSpace: "pre-wrap" }}>
        {JSON.stringify(record.appointment_details, null, 2)}
      </Text>
      <Text fw={600}>Service history</Text>
      <Text component="pre" size="sm" style={{ whiteSpace: "pre-wrap" }}>
        {JSON.stringify(record.service_history, null, 2)}
      </Text>
      <Text><strong>Retirement status:</strong> {record.retirement_status || "Not recorded"}</Text>
      <Text fw={600}>Leave balances and eligibility</Text>
      {record.leave_balances.length ? record.leave_balances.map((balance) => (
        <Text key={balance.leave_type}>
          {balance.leave_type}: {balance.available_days} days
          {balance.is_eligible ? " (eligible)" : " (not eligible)"}
        </Text>
      )) : <Text c="dimmed">No leave balance information is configured.</Text>}
      <Group justify="flex-end">
        <Button onClick={onClose}>Close</Button>
      </Group>
    </Stack>
  </Modal>;
}

function EmployeeEditor({ record, onClose }: {
  record: EmployeeRecord | null; onClose: () => void;
}) {
  const create = useCreateEmployee();
  const update = useUpdateEmployeeRecord(record?.user_id ?? 0);
  const [userId, setUserId] = useState(record ? String(record.user_id) : "");
  const [department, setDepartment] = useState(record?.department ?? "");
  const [designation, setDesignation] = useState(record?.designation ?? "");
  const [employmentStatus, setEmploymentStatus] = useState(record?.employment_status ?? "active");
  const [appointmentType, setAppointmentType] = useState(record?.appointment_type ?? "");
  const [startDate, setStartDate] = useState(record?.appointment_start_date ?? "");
  const [endDate, setEndDate] = useState(record?.appointment_end_date ?? "");
  const [details, setDetails] = useState(JSON.stringify(record?.appointment_details ?? {}, null, 2));
  const [history, setHistory] = useState(JSON.stringify(record?.service_history ?? [], null, 2));
  const [retirementStatus, setRetirementStatus] = useState(record?.retirement_status ?? "");
  const busy = create.isPending || update.isPending;

  function submit() {
    let appointment: Record<string, unknown>;
    let serviceHistory: Record<string, unknown>[];
    try {
      appointment = JSON.parse(details) as Record<string, unknown>;
      serviceHistory = JSON.parse(history) as Record<string, unknown>[];
      if (!appointment || Array.isArray(appointment) ||
          !Array.isArray(serviceHistory) ||
          serviceHistory.some((row) => !row || Array.isArray(row) || typeof row !== "object")) {
        throw new Error("Appointment details must be an object and service history an array of objects.");
      }
    } catch (e) {
      notifications.show({ color: "red", title: "Invalid JSON", message: e instanceof Error ? e.message : errorMessage(e) });
      return;
    }
    const body = {
      department, designation, employment_status: employmentStatus,
      appointment_type: appointmentType,
      appointment_start_date: startDate || null,
      appointment_end_date: endDate || null,
      appointment_details: appointment, service_history: serviceHistory,
      retirement_status: retirementStatus,
    };
    const onSuccess = () => {
      notifications.show({ color: "green", title: "Record saved", message: "The service record was saved." });
      onClose();
    };
    const onError = (e: unknown) =>
      notifications.show({ color: "red", title: "Could not save record", message: errorMessage(e) });
    if (record) {
      update.mutate(body, { onSuccess, onError });
      return;
    }
    const id = Number(userId);
    if (!Number.isSafeInteger(id) || id < 1) {
      notifications.show({ color: "red", title: "Invalid employee ID", message: "Enter a positive employee ID." });
      return;
    }
    create.mutate({ ...body, user_id: id }, { onSuccess, onError });
  }

  return (
    <Modal opened onClose={onClose} title={record ? "Edit service record" : "Add employee service record"} size="lg">
      <Stack>
        <TextInput label="Employee user ID" value={userId} disabled={!!record}
          onChange={(e) => setUserId(e.currentTarget.value)} />
        <Group grow>
          <TextInput label="Department" required value={department}
            onChange={(e) => setDepartment(e.currentTarget.value)} />
          <TextInput label="Designation" required value={designation}
            onChange={(e) => setDesignation(e.currentTarget.value)} />
        </Group>
        <Select label="Employment status" data={["active", "retired", "separated"]}
          value={employmentStatus}
          onChange={(value) => value && setEmploymentStatus(
            value as EmployeeRecord["employment_status"])} />
        <TextInput label="Appointment type" value={appointmentType}
          onChange={(e) => setAppointmentType(e.currentTarget.value)} />
        <Group grow>
          <TextInput type="date" label="Appointment start" value={startDate}
            onChange={(e) => setStartDate(e.currentTarget.value)} />
          <TextInput type="date" label="Appointment end" value={endDate}
            onChange={(e) => setEndDate(e.currentTarget.value)} />
        </Group>
        <TextInput label="Retirement status" value={retirementStatus}
          onChange={(e) => setRetirementStatus(e.currentTarget.value)} />
        <Textarea label="Appointment details (JSON object)" minRows={3} value={details}
          onChange={(e) => setDetails(e.currentTarget.value)} />
        <Textarea label="Service history (JSON array)" minRows={4} value={history}
          onChange={(e) => setHistory(e.currentTarget.value)} />
        <Group justify="flex-end">
          <Button variant="default" onClick={onClose}>Cancel</Button>
          <Button loading={busy} onClick={submit}>Save record</Button>
        </Group>
      </Stack>
    </Modal>
  );
}
