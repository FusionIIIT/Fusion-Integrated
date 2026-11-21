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
import { useMyApplications, useTransition } from "../../../api/hooks";
import type { PatentApplication } from "../../../api/types";

export default function MyApplicationsPage() {
  const { data, isPending, error } = useMyApplications();
  const transition = useTransition();
  const [historyFor, setHistoryFor] = useState<number | null>(null);

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  function withdraw(app: PatentApplication) {
    transition.mutate(
      { id: app.id, to_status: "withdrawn", reason: "Withdrawn by the student" },
      {
        onSuccess: () => notifications.show({
          color: "gray", title: "Withdrawn",
          message: `Your application to ${app.title} has been withdrawn.`,
        }),
        onError: (e) => notifications.show({
          color: "red", title: "Could not withdraw", message: errorMessage(e),
        }),
      },
    );
  }

  function resubmit(app: PatentApplication) {
    transition.mutate(
      { id: app.id, to_status: "draft", reason: "Resubmitted by the student" },
      {
        onSuccess: () => notifications.show({
          color: "gray", title: "Resubmitted",
          message: `Your application to ${app.title} has been resubmitted.`,
        }),
        onError: (e) => notifications.show({
          color: "red", title: "Could not resubmit", message: errorMessage(e),
        }),
      },
    );
  }

  function appeal(app: PatentApplication) {
    transition.mutate(
      { id: app.id, to_status: "appeal_pending", reason: "Appealed by the student" },
      {
        onSuccess: () => notifications.show({
          color: "gray", title: "Appealed",
          message: `Your appeal for ${app.title} has been filed.`,
        }),
        onError: (e) => notifications.show({
          color: "red", title: "Could not appeal", message: errorMessage(e),
        }),
      },
    );
  }

  function approveOfficeAction(app: PatentApplication) {
    transition.mutate(
      { id: app.id, to_status: "under_review", reason: "Office action response approved" },
      {
        onSuccess: () => notifications.show({
          color: "gray", title: "Approved",
          message: `Your response to the office action for ${app.title} has been approved.`,
        }),
        onError: (e) => notifications.show({
          color: "red", title: "Could not approve", message: errorMessage(e),
        }),
      },
    );
  }

  const canWithdraw = app.status === "submitted" || app.status === "under_review";
  const canResubmit = app.status === "rejected" || app.status === "withdrawn";
  const canAppeal = app.status === "rejected" || app.status === "shortlisted";
  const canApproveOfficeAction = app.status === "under_review";

  return (
    <Container size="xl">
      <PageHeader
        title="My Applications"
        subtitle="Every application you have submitted, and where it stands"
      />
      <Card padding="lg">
        <DataTable<PatentApplication>
          rows={(data?.results ?? []) as PatentApplication[]}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={900}
          columns={[
            {
              key: "title", header: "Title",
              render: (r) => <Text fw={600}>{r.title}</Text>,
            },
            {
              key: "filing_date", header: "Filing Date",
              render: (r) => r.filing_date
                ? new Date(r.filing_date).toLocaleDateString() : "—" ,
            },
            { key: "status", header: "Status",
              render: (r) => <StatusBadge status={r.status} /> },
            {
              key: "actions", header: "", align: "right",
              render: (r) => (
                <Group justify="flex-end" gap="xs">
                  {canWithdraw && (
                    <Button
                      size="xs" variant="subtle" color="gray"
                      loading={transition.isPending}
                      onClick={() => withdraw(r)}
                    >
                      Withdraw
                    </Button>
                  )}
                  {canResubmit && (
                    <Button
                      size="xs" variant="subtle" color="blue"
                      loading={transition.isPending}
                      onClick={() => resubmit(r)}
                    >
                      Resubmit
                    </Button>
                  )}
                  {canAppeal && (
                    <Button
                      size="xs" variant="subtle" color="red"
                      loading={transition.isPending}
                      onClick={() => appeal(r)}
                    >
                      Appeal
                    </Button>
                  )}
                  {canApproveOfficeAction && (
                    <Button
                      size="xs" variant="subtle" color="green"
                      loading={transition.isPending}
                      onClick={() => approveOfficeAction(r)}
                    >
                      Approve Response
                    </Button>
                  )}
                  <ActionIcon
                    variant="subtle" color="gray" aria-label="History"
                    onClick={() => setHistoryFor(r.id)}
                  >
                    <FaHistory size={12} />
                  </ActionIcon>
                </Group>
              ),
            },
          ]}
          empty={{
            icon: FaUserCheck,
            title: "You have not submitted any applications yet",
            description: "Submit a new application to see it here.",
          }}
        />
      </Card>

      <HistoryDrawer
        applicationId={historyFor} onClose={() => setHistoryFor(null)}
      />
    </Container>
  );
}
