import { useState } from "react";
import {
  Button, Card, Container, SimpleGrid, Stack, Text, Textarea,
  TextInput, Select, Checkbox,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaPlus } from "react-icons/fa";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { errorMessage } from "../../../lib/http";
import { useApply, useBalances, useMyRequests, useWithdraw } from "../api/hooks";
import type { ApplyPayload, LeaveRequest } from "../api/types";

const MinePage = () => {
  const balances = useBalances();
  const { data, isPending, error } = useMyRequests();
  const apply = useApply();
  const withdraw = useWithdraw();
  const [applying, setApplying] = useState(false);
  const [form, setForm] = useState<ApplyPayload>({
    category: "cl", from_date: "", to_date: "", half: "",
    purpose: "", station_leave_required: false, station_leave_details: "",
    substitute_required: false,
  });

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  const submit = () => {
    apply.mutate(form, {
      onSuccess: () => {
        notifications.show({ color: "green", title: "Application submitted",
          message: "Your leave request is now in the workflow." });
        setApplying(false);
      },
      onError: (e) => notifications.show({ color: "red",
        title: "Could not submit", message: errorMessage(e) }),
    });
  };

  const doWithdraw = (r: LeaveRequest) => {
    withdraw.mutate({ id: r.id, reason: "Withdrawn by applicant" }, {
      onSuccess: () => notifications.show({ color: "gray", title: "Withdrawn",
        message: "Your request has been withdrawn." }),
      onError: (e) => notifications.show({ color: "red",
        title: "Could not withdraw", message: errorMessage(e) }),
    });
  };

  return (
    <Container size="xl">
      <PageHeader title="My Leave"
        subtitle="Your balances, applications and leave history"
        action={<Button leftSection={<FaPlus />} onClick={() => setApplying(true)}>Apply for leave</Button>} />

      {balances.data && (
        <SimpleGrid cols={{ base: 2, sm: 3, md: 6 }} spacing="md">
          {balances.data.results.map((b) => (
            <Card key={b.category} padding="md">
              <Text size="xs" c="dimmed">{b.category_label}</Text>
              <Text fw={700} size="lg">{b.available}</Text>
              <Text size="xs" c="dimmed">of {b.credited} credited</Text>
            </Card>
          ))}
        </SimpleGrid>
      )}

      <DataTable<LeaveRequest>
         rows={data?.results ?? []}
         loading={isPending}
         rowKey={(r) => r.id}
         minWidth={900}
         empty={{ title: "No leave requests yet", description: "Apply for leave to get started." }}
         columns={[
           { key: "category", header: "Category", render: (r) => r.category_label },
           { key: "period", header: "Period", render: (r) => `${r.from_date} to ${r.to_date}` },
           { key: "days", header: "Days", align: "right", render: (r) => r.days },
           { key: "status", header: "Status", render: (r) => <StatusBadge status={r.status} /> },
           { key: "actions", header: "", render: (r) => (
               ["draft", "awaiting_unit_head", "awaiting_establishment", "awaiting_final"].includes(r.status)
                 ? <Button size="xs" variant="light" color="gray" onClick={() => doWithdraw(r)}>Withdraw</Button>
                 : null) },
         ]}
      />

      <FormModal opened={applying} onClose={() => setApplying(false)}
         title="Apply for leave" submitLabel="Submit application"
         submitting={apply.isPending} onSubmit={submit}>
        <Stack gap="sm">
          <Select
            label="Category"
            data={[{ value: "cl", label: "Casual Leave" }, { value: "rh", label: "Restricted Holiday" }, { value: "scl", label: "Special Casual Leave" }, { value: "el", label: "Earned Leave" }, { value: "col", label: "Commuted Leave" }, { value: "vl", label: "Vacation Leave" }]}
            value={form.category}
            onChange={(v) => setForm({ ...form, category: v as ApplyPayload["category"] })}
          />
          <TextInput
            label="From Date"
            type="date"
            value={form.from_date}
            onChange={(e) => setForm({ ...form, from_date: e.currentTarget.value })}
          />
          <TextInput
            label="To Date"
            type="date"
            value={form.to_date}
            onChange={(e) => setForm({ ...form, to_date: e.currentTarget.value })}
          />
          <Select
            label="Half"
            data={[{ value: "", label: "Full day" }, { value: "first", label: "First half" }, { value: "second", label: "Second half" }]}
            value={form.half}
            onChange={(v) => setForm({ ...form, half: (v ?? "") as ApplyPayload["half"] })}
          />
          <Textarea
            label="Purpose"
            value={form.purpose}
            onChange={(e) => setForm({ ...form, purpose: e.currentTarget.value })}
          />
          <Checkbox
            label="Station Leave Required"
            checked={form.station_leave_required}
            onChange={(e) => setForm({ ...form, station_leave_required: e.currentTarget.checked })}
          />
          {form.station_leave_required && (
            <Textarea
              label="Station Leave Details"
              value={form.station_leave_details}
              onChange={(e) => setForm({ ...form, station_leave_details: e.currentTarget.value })}
            />
          )}
        </Stack>
      </FormModal>
    </Container>
  );
};

export default MinePage;
