import { useState } from "react";
import {
  Button, Card, Container, Drawer, Group, Stack, Table, Text, Textarea, TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useCreateServiceRecord, useServiceRecords, useUpdateServiceRecord,
} from "../api/hooks";
import type { RecordFields, ServiceRecord } from "../api/types";
import { LeaveCreditManagement } from "./LeaveCreditManagement";
import { PolicyManagement } from "./PolicyManagement";

interface FormState {
  userId: string;
  department: string;
  designation: string;
  retirement: string;
  appointmentJson: string;
  serviceHistoryJson: string;
}

const emptyForm: FormState = {
  userId: "", department: "", designation: "", retirement: "",
  appointmentJson: "{\n  \"date\": \"\"\n}", serviceHistoryJson: "[]",
};

function formFromRecord(row: ServiceRecord): FormState {
  return {
    userId: String(row.user_id),
    department: row.department,
    designation: row.designation_snapshot,
    retirement: row.retirement_status,
    appointmentJson: JSON.stringify(row.appointment_details, null, 2),
    serviceHistoryJson: JSON.stringify(row.service_history, null, 2),
  };
}

function parseFields(form: FormState): RecordFields {
  const details: unknown = JSON.parse(form.appointmentJson);
  const history: unknown = JSON.parse(form.serviceHistoryJson);
  if (!details || typeof details !== "object" || Array.isArray(details)) {
    throw new Error("Appointment details must be a JSON object.");
  }
  if (!Array.isArray(history)) {
    throw new Error("Service history must be a JSON list.");
  }
  return {
    appointment_details: details as Record<string, unknown>,
    department: form.department.trim(),
    designation_snapshot: form.designation.trim(),
    service_history: history,
    retirement_status: form.retirement.trim(),
  };
}

function normalizedJson(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(normalizedJson).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.entries(value as Record<string, unknown>)
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([key, item]) => `${JSON.stringify(key)}:${normalizedJson(item)}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

export function changedRecordFields(
  original: ServiceRecord, submitted: RecordFields,
): Partial<RecordFields> {
  const changed: Partial<RecordFields> = {};
  for (const field of Object.keys(submitted) as (keyof RecordFields)[]) {
    if (normalizedJson(original[field]) !== normalizedJson(submitted[field])) {
      Object.assign(changed, { [field]: submitted[field] });
    }
  }
  return changed;
}

export default function AdministrationPage() {
  const { can } = useAuth();
  const { data, isPending, error } = useServiceRecords();
  const createRecord = useCreateServiceRecord();
  const updateRecord = useUpdateServiceRecord();
  const [editing, setEditing] = useState<ServiceRecord | null>(null);
  const [opened, setOpened] = useState(false);
  const [form, setForm] = useState<FormState>(emptyForm);
  const busy = createRecord.isPending || updateRecord.isPending;

  function openCreate() {
    setEditing(null);
    setForm(emptyForm);
    setOpened(true);
  }

  function openEdit(record: ServiceRecord) {
    setEditing(record);
    setForm(formFromRecord(record));
    setOpened(true);
  }

  function save() {
    let fields: RecordFields;
    try {
      fields = parseFields(form);
    } catch (e) {
      notifications.show({ position: "top-center",
        color: "red", title: "Invalid record fields",
        message: e instanceof Error ? e.message : "Check the record values.",
      });
      return;
    }
    const onSuccess = () => {
      notifications.show({ position: "top-center",
        color: "green", title: "Service record saved",
        message: "The change and its audit revision have been recorded.",
      });
      setOpened(false);
    };
    const onError = (e: unknown) => notifications.show({ position: "top-center",
      color: "red", title: "Could not save service record",
      message: errorMessage(e),
    });
    if (editing) {
      const changes = changedRecordFields(editing, fields);
      if (Object.keys(changes).length === 0) {
        notifications.show({ position: "top-center",
          color: "blue", title: "No changes to record",
          message: "Edit an official field before saving a new revision.",
        });
        return;
      }
      updateRecord.mutate({
        id: editing.id, expected_revision: editing.revision, fields: changes,
      }, { onSuccess, onError });
    } else {
      createRecord.mutate({
        user_id: Number(form.userId), ...fields,
      }, { onSuccess, onError });
    }
  }

  function update<K extends keyof FormState>(name: K, value: FormState[K]) {
    setForm((current) => ({ ...current, [name]: value }));
  }

  return (
    <Container size="xl">
      <PageHeader title="HR Administration"
        subtitle="Create and maintain official employee service records" />
      <Group justify="flex-end" mb="md">
        {can("hreis.service_record.create")
          && <Button onClick={openCreate}>Create employee record</Button>}
      </Group>
      {error && <ErrorState error={error} />}
      {isPending && <Text c="dimmed">Loading service records...</Text>}
      {data && <Card withBorder>
        {data.results.length === 0
          ? <Text c="dimmed">No employee service records have been created.</Text>
          : <Table.ScrollContainer minWidth={620}>
            <Table striped highlightOnHover>
              <Table.Thead><Table.Tr>
                <Table.Th>Employee ID</Table.Th>
                <Table.Th>Department</Table.Th>
                <Table.Th>Designation</Table.Th>
                <Table.Th>Revision</Table.Th>
                <Table.Th>Action</Table.Th>
              </Table.Tr></Table.Thead>
              <Table.Tbody>{data.results.map((record) => (
                <Table.Tr key={record.id}>
                  <Table.Td>#{record.user_id}</Table.Td>
                  <Table.Td>{record.department}</Table.Td>
                  <Table.Td>{record.designation_snapshot}</Table.Td>
                  <Table.Td>{record.revision}</Table.Td>
                  <Table.Td>
                    {can("hreis.service_record.update") && <Button size="xs" variant="light" onClick={() => openEdit(record)}>
                      Edit
                    </Button>}
                  </Table.Td>
                </Table.Tr>
              ))}</Table.Tbody>
            </Table>
          </Table.ScrollContainer>}
      </Card>}
      <PolicyManagement />
      <LeaveCreditManagement />
      <Drawer opened={opened} onClose={() => !busy && setOpened(false)}
        position="right" size="lg"
        title={editing ? "Update service record" : "Create service record"}>
        <Stack gap="md">
          <Text size="sm" c="dimmed">
            Official HR fields only. Identity, role assignments and payroll
            remain managed by their owning systems.
          </Text>
          <TextInput label="Employee directory ID" required
            disabled={Boolean(editing)} value={form.userId}
            onChange={(e) => update("userId", e.currentTarget.value)} />
          <TextInput label="Department" required value={form.department}
            onChange={(e) => update("department", e.currentTarget.value)} />
          <TextInput label="Designation snapshot" required value={form.designation}
            onChange={(e) => update("designation", e.currentTarget.value)} />
          <TextInput label="Retirement status" value={form.retirement}
            onChange={(e) => update("retirement", e.currentTarget.value)} />
          <Textarea label="Appointment details (JSON object)" minRows={5}
            autosize value={form.appointmentJson}
            onChange={(e) => update("appointmentJson", e.currentTarget.value)} />
          <Textarea label="Service history (JSON list)" minRows={4}
            autosize value={form.serviceHistoryJson}
            onChange={(e) => update("serviceHistoryJson", e.currentTarget.value)} />
          {editing && <Text size="xs" c="dimmed">
            Updating revision {editing.revision}. Another administrator's
            intervening changes require a refresh before saving.
          </Text>}
          <Group justify="flex-end">
            <Button variant="default" disabled={busy}
              onClick={() => setOpened(false)}>Cancel</Button>
            <Button loading={busy} onClick={save}>Save record</Button>
          </Group>
        </Stack>
      </Drawer>
    </Container>
  );
}
