import { useState } from "react";
import {
  ActionIcon, Button, Card, Container, Group, Stack, Text,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaHistory, FaUserCheck } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { CpiBadge } from "../components/CpiBadge";
import { HistoryDrawer } from "../components/HistoryDrawer";
import { useApplications, useTransition } from "../api/hooks";
import type { Application } from "../api/types";

export default function MyApplicationsPage() {
  const { data, isPending, error } = useApplications();
  const transition = useTransition();
  const [historyFor, setHistoryFor] = useState<number | null>(null);

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  function withdraw(app: Application) {
    transition.mutate(
      { id: app.id, to_status: "withdrawn", reason: "Withdrawn by the student" },
      {
        onSuccess: () => notifications.show({
          color: "gray", title: "Withdrawn",
          message: `Your application to ${app.posting.title} has been withdrawn.`,
        }),
        onError: (e) => notifications.show({
          color: "red", title: "Could not withdraw", message: errorMessage(e),
        }),
      },
    );
  }

  return (
    <Container size="xl">
      <PageHeader
        title="My Applications"
        subtitle="Every application you have submitted, and where it stands"
      />
      <Card padding="lg">
        <DataTable<Application>
          rows={(data?.results ?? []) as Application[]}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={900}
          columns={[
            {
              key: "posting", header: "Role",
              render: (r) => (
                <Stack gap={0}>
                  <Text fw={600}>{r.posting?.title}</Text>
                  <Text size="xs" c="dimmed">{r.posting?.company?.name}</Text>
                </Stack>
              ),
            },
            {
              key: "cpi_at_apply", header: "CPI at apply",
              // The frozen value: what the decision was made on, not today's CPI.
              render: (r) => (
                <CpiBadge
                  cpi={r.cpi_at_apply}
                  standing={{
                    semester: r.semester_at_apply, semester_type: null,
                    declared_seq: null, synced_at: null, computed_by: null,
                  }}
                />
              ),
            },
            { key: "applied_at", header: "Applied",
              render: (r) => r.applied_at
                ? new Date(r.applied_at).toLocaleDateString() : "—" },
            { key: "status", header: "Status",
              render: (r) => <StatusBadge status={r.status} /> },
            {
              key: "actions", header: "", align: "right",
              render: (r) => (
                <Group justify="flex-end" gap="xs">
                  {/* "Why is my application at this status?" answered without
                      a support request. */}
                  <ActionIcon
                    variant="subtle" color="gray" aria-label="History"
                    onClick={() => setHistoryFor(r.id)}
                  >
                    <FaHistory size={12} />
                  </ActionIcon>
                  {r.allowed_transitions?.includes("withdrawn") && (
                    <Button
                      size="xs" variant="subtle" color="gray"
                      loading={transition.isPending}
                      onClick={() => withdraw(r)}
                    >
                      Withdraw
                    </Button>
                  )}
                </Group>
              ),
            },
          ]}
          empty={{
            icon: FaUserCheck,
            title: "You have not applied to anything yet",
            description: "Applications you submit will be tracked here.",
          }}
        />
      </Card>

      <HistoryDrawer
        applicationId={historyFor} onClose={() => setHistoryFor(null)}
      />
    </Container>
  );
}
