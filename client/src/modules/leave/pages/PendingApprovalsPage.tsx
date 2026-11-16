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
import { FaArrowRight, FaCheck, FaTimes } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useDecideLeave, usePendingApprovals } from "../api";
import type { ApprovalOutcome, LeaveRequest } from "../types";

export default function PendingApprovalsPage() {
  const { data, isPending, error } = usePendingApprovals();
  const decideMutation = useDecideLeave();

  const [activeRequest, setActiveRequest] = useState<LeaveRequest | null>(null);
  const [decisionOutcome, setDecisionOutcome] = useState<ApprovalOutcome>("approved");
  const [remarks, setRemarks] = useState("");

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  const handleOpenDecision = (req: LeaveRequest, outcome: ApprovalOutcome) => {
    setActiveRequest(req);
    setDecisionOutcome(outcome);
    setRemarks("");
  };

  const handleConfirmDecision = () => {
    if (!activeRequest) return;

    decideMutation.mutate(
      {
        id: activeRequest.id,
        outcome: decisionOutcome,
        remarks: remarks.trim(),
      },
      {
        onSuccess: () => {
          const outcomeLabel =
            decisionOutcome === "approved"
              ? "Approved"
              : decisionOutcome === "forwarded"
                ? "Forwarded"
                : "Rejected";
          const outcomeColor =
            decisionOutcome === "approved"
              ? "teal"
              : decisionOutcome === "forwarded"
                ? "indigo"
                : "red";

          notifications.show({
            color: outcomeColor,
            title: `Request ${outcomeLabel}`,
            message: `Leave request #${activeRequest.id} has been ${decisionOutcome}.`,
          });
          setActiveRequest(null);
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Decision Failed",
            message: errorMessage(err),
          });
        },
      },
    );
  };

  const rows = data || [];

  return (
    <Container size="xl">
      <PageHeader
        title="Pending Approvals"
        subtitle="Review, decide, or forward pending leave requests (HR-UC-004 / BW-HR-01 / BW-HR-03)"
      />

      <Card padding="lg" withBorder radius="md">
        <DataTable<LeaveRequest>
          rows={rows}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={950}
          empty={{
            title: "No leave requests pending",
            description: "You have reviewed all applications routed to your authority tier.",
          }}
          columns={[
            {
              key: "applicant",
              header: "Applicant ID",
              render: (r) => (
                <Stack gap={2}>
                  <Text fw={600}>Employee #{r.user_id}</Text>
                  {r.forward_count > 0 && (
                    <Badge color="violet" variant="light" size="xs">
                      Forwarded ({r.forward_count}x)
                    </Badge>
                  )}
                </Stack>
              ),
            },
            {
              key: "type",
              header: "Leave Type",
              render: (r) => (
                <Badge color="blue" variant="light" style={{ textTransform: "capitalize" }}>
                  {r.leave_type}
                </Badge>
              ),
            },
            {
              key: "duration",
              header: "Duration",
              render: (r) => (
                <Stack gap={2}>
                  <Text size="sm" fw={500}>
                    {r.duration_days} day(s)
                  </Text>
                  <Text size="xs" c="dimmed">
                    {r.start_date} to {r.end_date}
                  </Text>
                </Stack>
              ),
            },
            {
              key: "justification",
              header: "Justification",
              render: (r) => (
                <Text size="sm" lineClamp={2}>
                  {r.justification}
                </Text>
              ),
            },
            {
              key: "tier",
              header: "Routing Tier",
              render: (r) => (
                <Badge variant="outline" color="indigo">
                  {r.current_authority_role || "Designated Authority"}
                </Badge>
              ),
            },
            {
              key: "actions",
              header: "Actions",
              render: (r) => (
                <Group gap="xs">
                  <Button
                    size="xs"
                    color="teal"
                    leftSection={<FaCheck />}
                    onClick={() => handleOpenDecision(r, "approved")}
                  >
                    Approve
                  </Button>
                  <Button
                    size="xs"
                    color="indigo"
                    variant="light"
                    leftSection={<FaArrowRight />}
                    onClick={() => handleOpenDecision(r, "forwarded")}
                  >
                    Forward
                  </Button>
                  <Button
                    size="xs"
                    color="red"
                    variant="outline"
                    leftSection={<FaTimes />}
                    onClick={() => handleOpenDecision(r, "rejected")}
                  >
                    Reject
                  </Button>
                </Group>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        opened={Boolean(activeRequest)}
        onClose={() => setActiveRequest(null)}
        title={
          <Text fw={600}>
            {decisionOutcome === "approved"
              ? "Approve"
              : decisionOutcome === "forwarded"
                ? "Forward (BW-HR-03)"
                : "Reject"}{" "}
            Leave Request #{activeRequest?.id}
          </Text>
        }
      >
        <Stack gap="md">
          <Text size="sm">
            {decisionOutcome === "forwarded" ? (
              <>
                You are forwarding this request from{" "}
                <b>Employee #{activeRequest?.user_id}</b> to the next administrative tier
                for further review.
              </>
            ) : (
              <>
                You are about to <b>{decisionOutcome}</b> the request for{" "}
                <b>{activeRequest?.duration_days} day(s)</b> of{" "}
                <b>{activeRequest?.leave_type} leave</b>.
              </>
            )}
          </Text>

          {activeRequest?.decisions && activeRequest.decisions.length > 0 && (
            <Card withBorder bg="gray.0" padding="xs">
              <Text size="xs" fw={600} mb={4}>
                Prior Review Traversal:
              </Text>
              {activeRequest.decisions.map((d, i) => (
                <Text key={i} size="xs" c="dimmed">
                  • Authority #{d.authority_id}: <b>{d.outcome.toUpperCase()}</b>
                  {d.remarks ? ` — "${d.remarks}"` : ""}
                </Text>
              ))}
            </Card>
          )}

          <Textarea
            label={decisionOutcome === "forwarded" ? "Forwarding Endorsement / Remarks" : "Remarks (optional)"}
            placeholder={
              decisionOutcome === "forwarded"
                ? "e.g., Forwarded with recommendation for director's approval..."
                : "Add decision comments or audit remarks..."
            }
            value={remarks}
            onChange={(e) => setRemarks(e.target.value)}
            minRows={3}
          />

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setActiveRequest(null)}>
              Cancel
            </Button>
            <Button
              color={
                decisionOutcome === "approved"
                  ? "teal"
                  : decisionOutcome === "forwarded"
                    ? "indigo"
                    : "red"
              }
              loading={decideMutation.isPending}
              onClick={handleConfirmDecision}
            >
              Confirm{" "}
              {decisionOutcome === "approved"
                ? "Approval"
                : decisionOutcome === "forwarded"
                  ? "Forwarding"
                  : "Rejection"}
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
