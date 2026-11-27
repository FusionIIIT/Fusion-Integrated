import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  SegmentedControl,
  Stack,
  Text,
} from "@mantine/core";
import { FaHandsHelping, FaInbox } from "react-icons/fa";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useSubstituteNominations } from "../api/hooks";
import type { SubstituteNomination } from "../api/types";
import { SubstituteResponseModal } from "../components/ApprovalModals";

export default function ActionInboxPage() {
  const [filter, setFilter] = useState<"pending" | "all">("pending");
  const [activeNomination, setActiveNomination] = useState<SubstituteNomination | null>(null);

  const { data, isPending, error } = useSubstituteNominations();

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  const nominations = data ?? [];
  const filtered = filter === "pending"
    ? nominations.filter((n) => n.status === "pending")
    : nominations;

  return (
    <Container size="xl">
      <PageHeader
        title="Action Inbox — Substitute Requests"
        subtitle="Review and respond to colleagues' requests for academic and administrative responsibility coverage."
      />

      <Card withBorder padding="lg" radius="md">
        <Group justify="space-between" mb="md" wrap="wrap">
          <Text fw={700} size="md">
            Nominations Received
          </Text>
          <SegmentedControl
            size="xs"
            value={filter}
            onChange={(val) => setFilter(val as "pending" | "all")}
            data={[
              { value: "pending", label: `Pending (${nominations.filter((n) => n.status === "pending").length})` },
              { value: "all", label: `All Requests (${nominations.length})` },
            ]}
          />
        </Group>

        <DataTable<SubstituteNomination>
          rows={filtered}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={800}
          columns={[
            {
              key: "applicant",
              header: "Applicant / Request",
              render: (r) => (
                <Stack gap={0}>
                  <Text fw={600} size="sm">
                    Application #{r.request?.application_number}
                  </Text>
                  <Text size="xs" c="dimmed">
                    User #{r.request?.user_id} ({r.request?.department || "Faculty/Staff"})
                  </Text>
                </Stack>
              ),
            },
            {
              key: "type",
              header: "Leave Category",
              render: (r) => (
                <Text size="sm">
                  {r.request?.leave_type?.name} ({r.request?.leave_type?.code})
                </Text>
              ),
            },
            {
              key: "period",
              header: "Coverage Period",
              render: (r) => (
                <Stack gap={0}>
                  <Text size="sm">
                    {r.request?.start_date} → {r.request?.end_date}
                  </Text>
                  <Text size="xs" c="dimmed">
                    {r.request?.requested_days} days total
                  </Text>
                </Stack>
              ),
            },
            {
              key: "reason",
              header: "Applicant Reason",
              render: (r) => (
                <Text size="xs" lineClamp={2} style={{ maxWidth: 260 }}>
                  {r.request?.reason || "—"}
                </Text>
              ),
            },
            {
              key: "status",
              header: "Your Response",
              render: (r) => {
                const color =
                  r.status === "accepted" ? "green" : r.status === "declined" ? "red" : "orange";
                return (
                  <Badge color={color} variant="light" size="sm">
                    {r.status.toUpperCase()}
                  </Badge>
                );
              },
            },
            {
              key: "actions",
              header: "Action",
              align: "right",
              render: (r) => (
                <Group justify="flex-end">
                  {r.status === "pending" ? (
                    <Button
                      size="xs"
                      color="blue"
                      leftSection={<FaHandsHelping size={12} />}
                      onClick={() => setActiveNomination(r)}
                    >
                      Respond
                    </Button>
                  ) : (
                    <Text size="xs" c="dimmed">
                      {r.responded_at ? `Responded ${new Date(r.responded_at).toLocaleDateString()}` : "Completed"}
                    </Text>
                  )}
                </Group>
              ),
            },
          ]}
          empty={{
            icon: FaInbox,
            title: filter === "pending" ? "No pending substitute requests" : "No substitute nominations found",
            description: "When colleagues nominate you to cover their responsibilities, requests will appear here.",
          }}
        />
      </Card>

      <SubstituteResponseModal
        nomination={activeNomination}
        opened={activeNomination !== null}
        onClose={() => setActiveNomination(null)}
      />
    </Container>
  );
}
