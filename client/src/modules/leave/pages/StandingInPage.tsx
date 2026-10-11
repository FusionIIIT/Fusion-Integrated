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

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useNominations, useRespondNomination } from "../api/hooks";
import type { LeaveRequest } from "../api/types";

export default function StandingInPage() {
  const { data: nominations, isPending, error } = useNominations();
  const respondMut = useRespondNomination();

  const [selectedReq, setSelectedReq] = useState<LeaveRequest | null>(null);
  const [accepted, setAccepted] = useState<boolean>(true);
  const [remark, setRemark] = useState<string>("");

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  function handleDecisionSubmit() {
    if (!selectedReq) return;
    respondMut.mutate(
      { id: selectedReq.id, accepted, remark },
      {
        onSuccess: () => {
          notifications.show({
            color: accepted ? "green" : "orange",
            title: accepted ? "Nomination Accepted" : "Nomination Declined",
            message: `Response submitted for leave request #${selectedReq.id}.`,
          });
          setSelectedReq(null);
          setRemark("");
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Response Failed",
            message: errorMessage(err),
          });
        },
      },
    );
  }

  return (
    <Container size="xl">
      <PageHeader
        title="Standing In"
        subtitle="Colleagues have nominated you to stand in for them during their leave"
      />

      <Card padding="lg" withBorder>
        <DataTable<LeaveRequest>
          rows={nominations ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          empty={{ title: "No substitute requests", description: "You have no pending requests to stand in as substitute." }}
          minWidth={800}
          columns={[
            {
              key: "id",
              header: "Request ID",
              render: (r) => <Text fw={600}>#{r.id}</Text>,
            },
            {
              key: "applicant",
              header: "Applicant User ID",
              render: (r) => <Text size="sm">User #{r.user_id}</Text>,
            },
            {
              key: "category",
              header: "Category",
              render: (r) => <Badge color="blue">{r.category}</Badge>,
            },
            {
              key: "period",
              header: "Leave Period",
              render: (r) => (
                <Text size="sm">
                  {r.starts_on} to {r.ends_on} ({r.deductible_days} days)
                </Text>
              ),
            },
            {
              key: "reason",
              header: "Reason",
              render: (r) => <Text size="sm" lineClamp={2}>{r.reason}</Text>,
            },
            {
              key: "actions",
              header: "Action",
              render: (r) => (
                <Group gap="xs">
                  <Button
                    size="xs"
                    color="green"
                    onClick={() => {
                      setSelectedReq(r);
                      setAccepted(true);
                    }}
                  >
                    Accept
                  </Button>
                  <Button
                    size="xs"
                    color="red"
                    variant="subtle"
                    onClick={() => {
                      setSelectedReq(r);
                      setAccepted(false);
                    }}
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
        opened={Boolean(selectedReq)}
        onClose={() => setSelectedReq(null)}
        title={accepted ? "Accept Standing In Nomination" : "Decline Nomination"}
      >
        <Stack gap="md">
          <Text size="sm">
            {accepted
              ? `Accept standing in for leave request #${selectedReq?.id}? You agree to cover duty during this duration.`
              : `Decline nomination for leave request #${selectedReq?.id}? The applicant will be notified to renominate.`}
          </Text>
          <Textarea
            label="Remark (Optional)"
            placeholder="Add any note..."
            value={remark}
            onChange={(e) => setRemark(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setSelectedReq(null)}>Cancel</Button>
            <Button
              color={accepted ? "green" : "red"}
              loading={respondMut.isPending}
              onClick={handleDecisionSubmit}
            >
              Confirm
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
