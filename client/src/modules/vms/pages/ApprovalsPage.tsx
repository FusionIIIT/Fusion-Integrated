import { useState } from "react";
import {
  Badge,
  Button,
  Container,
  Group,
  Modal,
  Stack,
  Text,
  Textarea,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCheck, FaTimes, FaUserClock } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useContingencyApprove, useDecideVisit, useVisits } from "../api/hooks";
import type { VisitRequest } from "../api/types";

export default function ApprovalsPage() {
  const { data: visits, isPending, error } = useVisits({ status: "PENDING_APPROVAL" });
  const decide = useDecideVisit();
  const contingency = useContingencyApprove();

  const [rejectingVisit, setRejectingVisit] = useState<VisitRequest | null>(null);
  const [rejectReason, setRejectReason] = useState("");
  const [contingencyVisit, setContingencyVisit] = useState<VisitRequest | null>(null);
  const [contingencyReason, setContingencyReason] = useState("");

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  function handleApprove(v: VisitRequest) {
    decide.mutate(
      { id: v.id, decision: "APPROVE" },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Visit Approved",
            message: `Digital pass generated for ${v.visitor.name}.`,
          });
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Approval Failed",
            message: errorMessage(err),
          });
        },
      }
    );
  }

  function handleRejectSubmit() {
    if (!rejectingVisit) return;
    decide.mutate(
      { id: rejectingVisit.id, decision: "REJECT", reason: rejectReason },
      {
        onSuccess: () => {
          notifications.show({
            color: "red",
            title: "Visit Rejected",
            message: `Visit for ${rejectingVisit.visitor.name} was rejected.`,
          });
          setRejectingVisit(null);
          setRejectReason("");
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Rejection Failed",
            message: errorMessage(err),
          });
        },
      }
    );
  }

  function handleContingencySubmit() {
    if (!contingencyVisit) return;
    contingency.mutate(
      { id: contingencyVisit.id, reason: contingencyReason },
      {
        onSuccess: () => {
          notifications.show({
            color: "teal",
            title: "Contingency Approval Granted",
            message: `Emergency contingency pass approved for ${contingencyVisit.visitor.name}.`,
          });
          setContingencyVisit(null);
          setContingencyReason("");
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Contingency Failed",
            message: errorMessage(err),
          });
        },
      }
    );
  }

  return (
    <Container size="xl">
      <Stack gap="lg">
        <PageHeader
          title="Host Approvals & Pre-authorizations"
          subtitle="Review pending visitor requests, grant approvals, or authorize contingency exceptions."
        />

        <DataTable
          loading={isPending}
          rows={visits ?? []}
          rowKey={(v) => v.id}
          empty={{ title: "No pending visit requests requiring your approval." }}
          columns={[
            {
              key: "visitor",
              header: "Visitor",
              render: (v: VisitRequest) => (
                <Stack gap={2}>
                  <Text fw={600}>{v.visitor.name}</Text>
                  <Text size="xs" c="dimmed">{v.visitor.phone} • {v.visitor.email}</Text>
                </Stack>
              ),
            },
            {
              key: "schedule",
              header: "Schedule & Purpose",
              render: (v: VisitRequest) => (
                <Stack gap={2}>
                  <Text size="sm">{v.purpose}</Text>
                  <Text size="xs" c="dimmed">
                    {new Date(v.scheduled_start).toLocaleString()} to {new Date(v.scheduled_end).toLocaleTimeString()}
                  </Text>
                </Stack>
              ),
            },
            {
              key: "type",
              header: "Type",
              render: (v: VisitRequest) => (
                <Badge color={v.pass_type === "VIP" ? "violet" : "blue"}>{v.pass_type}</Badge>
              ),
            },
            {
              key: "actions",
              header: "Actions",
              render: (v: VisitRequest) => (
                <Group gap="xs">
                  <Button
                    size="xs"
                    color="green"
                    leftSection={<FaCheck />}
                    loading={decide.isPending}
                    onClick={() => handleApprove(v)}
                  >
                    Approve
                  </Button>
                  <Button
                    size="xs"
                    color="red"
                    variant="outline"
                    leftSection={<FaTimes />}
                    onClick={() => setRejectingVisit(v)}
                  >
                    Reject
                  </Button>
                  <Button
                    size="xs"
                    color="yellow"
                    variant="light"
                    leftSection={<FaUserClock />}
                    onClick={() => setContingencyVisit(v)}
                  >
                    Contingency
                  </Button>
                </Group>
              ),
            },
          ]}
        />

        {/* Modal: Rejection Reason */}
        <Modal
          opened={!!rejectingVisit}
          onClose={() => setRejectingVisit(null)}
          title="Reject Visit Request"
          size="sm"
        >
          <Stack gap="sm">
            <Text size="sm">
              Please provide a justification for rejecting the visit request for{" "}
              <b>{rejectingVisit?.visitor.name}</b>:
            </Text>
            <Textarea
              placeholder="e.g. Host unavailable, unscheduled meeting..."
              required
              minRows={3}
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
            />
            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => setRejectingVisit(null)}>Cancel</Button>
              <Button color="red" loading={decide.isPending} onClick={handleRejectSubmit}>
                Confirm Rejection
              </Button>
            </Group>
          </Stack>
        </Modal>

        {/* Modal: Contingency Approval */}
        <Modal
          opened={!!contingencyVisit}
          onClose={() => setContingencyVisit(null)}
          title="Admin Contingency Approval"
          size="sm"
        >
          <Stack gap="sm">
            <Text size="sm">
              Provide justification for approving on behalf of Host #{contingencyVisit?.host_id}:
            </Text>
            <TextInput
              placeholder="Reason (e.g. Host in urgent conference, verified via phone)"
              required
              value={contingencyReason}
              onChange={(e) => setContingencyReason(e.target.value)}
            />
            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => setContingencyVisit(null)}>Cancel</Button>
              <Button color="teal" loading={contingency.isPending} onClick={handleContingencySubmit}>
                Confirm Contingency Approval
              </Button>
            </Group>
          </Stack>
        </Modal>
      </Stack>
    </Container>
  );
}
