import { useState } from "react";
import {
  Button, Card, Container, Group, Modal, Select, Stack, Text, Textarea,
} from "@mantine/core";
import { DateInput } from "@mantine/dates";
import { notifications } from "@mantine/notifications";
import { FaCalendarPlus } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { useApply, useApplications, useWithdraw } from "../api/hooks";
import { CATEGORY_LABELS, type LeaveApplication } from "../api/types";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";

const CATEGORY_OPTIONS = Object.entries(CATEGORY_LABELS).map(([v, l]) =>
  ({ value: v, label: l }));

export default function MyLeavePage() {
  const { data, isPending, error } = useApplications();
  const apply = useApply();
  const withdraw = useWithdraw();
  const [open, setOpen] = useState(false);
  const [category, setCategory] = useState<string | null>("cl");
  const [start, setStart] = useState<Date | null>(null);
  const [end, setEnd] = useState<Date | null>(null);
  const [purpose, setPurpose] = useState("");

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  function submit() {
    if (!category || !start || !end) return;
    apply.mutate(
      {
        category, start_date: start.toISOString().slice(0, 10),
        end_date: end.toISOString().slice(0, 10), half: "full", purpose,
      },
      {
        onSuccess: () => {
          notifications.show({ color: "green", title: "Submitted",
                               message: "Your leave request has been submitted." });
          setOpen(false);
        },
        onError: (e) => notifications.show(
          { color: "red", title: "Could not apply", message: errorMessage(e) }),
      },
    );
  }

  return (
    <Container size="xl">
      <PageHeader
        title="My Leave"
        subtitle="Your leave applications and where they stand"
        action={
          <Button leftSection={<FaCalendarPlus size={14} />}
                  onClick={() => setOpen(true)}>
            Apply for leave
          </Button>
        }
      />

      <Card padding="lg">
        <DataTable<LeaveApplication>
          rows={data?.results ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          columns={[
            { key: "category", header: "Type",
              render: (r) => <Text fw={600}>{CATEGORY_LABELS[r.category]}</Text> },
            { key: "period", header: "Period",
              render: (r) => `${r.start_date} — ${r.end_date}` },
            { key: "days", header: "Days",
              render: (r) => r.chargeable_days },
            { key: "status", header: "Status",
              render: (r) => <StatusBadge status={r.status} /> },
            { key: "actions", header: "", align: "right",
              render: (r) => (
                <Group justify="flex-end">
                  {r.status === "submitted" && (
                    <Button size="xs" variant="subtle" color="gray"
                            loading={withdraw.isPending}
                            onClick={() => withdraw.mutate(r.id)}>
                      Withdraw
                    </Button>
                  )}
                </Group>
              ),
            },
          ]}
          empty={{
            icon: FaCalendarPlus,
            title: "No leave requests yet",
            description: "Apply for leave and it will appear here.",
          }}
        />
      </Card>

      <Modal opened={open} onClose={() => setOpen(false)}
             title="Apply for leave">
        <Stack gap="sm">
          <Select label="Category" data={CATEGORY_OPTIONS} value={category}
                  onChange={setCategory} />
          <DateInput label="From" value={start} onChange={setStart} />
          <DateInput label="To" value={end} onChange={setEnd} />
          <Textarea label="Purpose" value={purpose}
                    onChange={(e) => setPurpose(e.currentTarget.value)} />
          <Button onClick={submit} loading={apply.isPending}>Submit</Button>
        </Stack>
      </Modal>
    </Container>
  );
}
