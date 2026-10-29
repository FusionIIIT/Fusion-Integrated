import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  Stack,
  Text,
  Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCheck, FaTimes } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useRespondSubstitute, useSubstituteRequests } from "../api/hooks";
import type { LeaveRequest } from "../api/types";

export default function SubstituteRequestsPage() {
  const { data, isPending, error } = useSubstituteRequests();
  const respondMutation = useRespondSubstitute();

  const [declineModalItem, setDeclineModalItem] = useState<LeaveRequest | null>(null);
  const [declineReason, setDeclineReason] = useState("");

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  function handleAccept(req: LeaveRequest) {
    respondMutation.mutate(
      { id: req.id, accept: true, reason: "Substitute accepted nomination" },
      {
        onSuccess: () => {
          notifications.show({
            color: "teal",
            title: "Accepted",
            message: `You accepted substitution for Leave #${req.id}.`,
          });
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Action Failed",
            message: errorMessage(err),
          });
        },
      }
    );
  }

  function handleConfirmDecline() {
    if (!declineModalItem) return;
    respondMutation.mutate(
      { id: declineModalItem.id, accept: false, reason: declineReason },
      {
        onSuccess: () => {
          notifications.show({
            color: "gray",
            title: "Declined",
            message: `You declined substitution for Leave #${declineModalItem.id}.`,
          });
          setDeclineModalItem(null);
          setDeclineReason("");
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Action Failed",
            message: errorMessage(err),
          });
        },
      }
    );
  }

  const rows = (data?.results ?? []) as LeaveRequest[];

  return (
    <Container size="xl">
      <PageHeader
        title="Substitute Requests"
        subtitle="Requests from colleagues nominating you to take charge during their leave"
      />

      <Card padding="lg" withBorder radius="md">
        <DataTable<LeaveRequest>
          rows={rows}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={800}
          empty={{
            title: "No substitute requests",
            description: "No colleague has nominated you as substitute currently",
          }}
          columns={[

            {
              key: "id",
              header: "Request ID",
              render: (r) => <Text fw={600}>#{r.id}</Text>,
            },
            {
              key: "applicant",
              header: "Applicant",
              render: (r) => <Text size="sm">User #{r.user_id}</Text>,
            },
            {
              key: "category",
              header: "Category",
              render: (r) => (
                <Badge color="indigo" variant="light">
                  {r.category}
                </Badge>
              ),
            },
            {
              key: "dates",
              header: "Responsibility Period",
              render: (r) => (
                <Stack gap={0}>
                  <Text size="sm">
                    {r.start_date} to {r.end_date}
                  </Text>
                  <Text size="xs" c="dimmed">
                    {r.days_counted} day(s)
                  </Text>
                </Stack>
              ),
            },
            {
              key: "purpose",
              header: "Applicant's Reason",
              render: (r) => (
                <Text size="xs" c="dimmed" lineClamp={2}>
                  {r.purpose || "No reason specified"}
                </Text>
              ),
            },
            {
              key: "actions",
              header: "Decision",
              render: (r) => (
                <Group gap="xs">
                  <Button
                    size="xs"
                    color="teal"
                    leftSection={<FaCheck />}
                    loading={respondMutation.isPending}
                    onClick={() => handleAccept(r)}
                  >
                    Accept
                  </Button>
                  <Button
                    size="xs"
                    color="red"
                    variant="light"
                    leftSection={<FaTimes />}
                    onClick={() => setDeclineModalItem(r)}
                  >
                    Decline
                  </Button>
                </Group>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        opened={Boolean(declineModalItem)}
        onClose={() => setDeclineModalItem(null)}
        title={`Decline Substitute Nomination for Leave #${declineModalItem?.id}`}
      >
        <Stack gap="md">
          <Text size="sm">
            Declining this request will return the leave application to the applicant so they can nominate another colleague.
          </Text>
          <Textarea
            label="Reason for declining"
            placeholder="e.g. Prior teaching commitments or conflicting travel"
            value={declineReason}
            onChange={(e) => setDeclineReason(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setDeclineModalItem(null)}>
              Cancel
            </Button>
            <Button color="red" onClick={handleConfirmDecline} loading={respondMutation.isPending}>
              Confirm Decline
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
