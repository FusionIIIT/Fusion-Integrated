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
import { FaCheck, FaThumbsUp, FaTimes } from "react-icons/fa";


import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import {
  useCancelDecision,
  useExtensionDecision,
  usePendingApprovals,
  useResumptionReview,
  useSanctionDecision,
  useUnitHeadReview,
} from "../api/hooks";
import type { LeaveRequest } from "../api/types";


export default function PendingApprovalsPage() {

  const { data, isPending, error } = usePendingApprovals();
  const unitHeadReviewMutation = useUnitHeadReview();
  const sanctionMutation = useSanctionDecision();
  const cancelDecisionMutation = useCancelDecision();
  const extensionDecisionMutation = useExtensionDecision();
  const resumptionReviewMutation = useResumptionReview();

  // Generic decision modal
  const [activeItem, setActiveItem] = useState<{
    item: LeaveRequest;
    type: "uh_cl" | "uh_recommend" | "sanction" | "cancel" | "extension" | "resumption";
  } | null>(null);

  const [decisionReason, setDecisionReason] = useState("");

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  function handleUnitHeadAction(req: LeaveRequest, action: string) {
    unitHeadReviewMutation.mutate(
      { id: req.id, action, reason: decisionReason },
      {
        onSuccess: () => {
          notifications.show({
            color: "teal",
            title: "Decision Recorded",
            message: `Review recorded for Leave #${req.id}.`,
          });
          setActiveItem(null);
          setDecisionReason("");
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

  function handleSanctionAction(req: LeaveRequest, approve: boolean) {
    sanctionMutation.mutate(
      { id: req.id, approve, reason: decisionReason },
      {
        onSuccess: () => {
          notifications.show({
            color: approve ? "teal" : "gray",
            title: approve ? "Leave Sanctioned" : "Leave Rejected",
            message: `Decision recorded for Leave #${req.id}.`,
          });
          setActiveItem(null);
          setDecisionReason("");
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

  function handleCancelDecision(req: LeaveRequest, approve: boolean) {
    cancelDecisionMutation.mutate(
      { id: req.id, approve, reason: decisionReason },
      {
        onSuccess: () => {
          notifications.show({
            color: "teal",
            title: "Cancellation Decided",
            message: `Cancellation decision recorded for Leave #${req.id}.`,
          });
          setActiveItem(null);
          setDecisionReason("");
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

  function handleExtensionDecision(req: LeaveRequest, approve: boolean) {
    extensionDecisionMutation.mutate(
      { id: req.id, approve, reason: decisionReason },
      {
        onSuccess: () => {
          notifications.show({
            color: "teal",
            title: "Extension Decided",
            message: `Extension decision recorded for Leave #${req.id}.`,
          });
          setActiveItem(null);
          setDecisionReason("");
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

  function handleResumptionReview(req: LeaveRequest) {
    resumptionReviewMutation.mutate(
      { id: req.id, reason: decisionReason },
      {
        onSuccess: () => {
          notifications.show({
            color: "teal",
            title: "Resumption Verified",
            message: `Resumption verified for Leave #${req.id}. Unused balance refunded.`,
          });
          setActiveItem(null);
          setDecisionReason("");
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
        title="Pending Approvals"
        subtitle="Queue of leave requests requiring your review, recommendation, or sanction"
      />

      <Card padding="lg" withBorder radius="md">
        <DataTable<LeaveRequest>
          rows={rows}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={950}
          empty={{
            title: "No pending approvals",
            description: "You have reviewed all leave requests in your queue",
          }}
          columns={[
            {
              key: "id",
              header: "ID",
              render: (r) => <Text fw={600}>#{r.id}</Text>,
            },
            {
              key: "employee",
              header: "Employee",
              render: (r) => (
                <Stack gap={0}>
                  <Text size="sm" fw={500}>
                    User #{r.user_id}
                  </Text>
                  <Text size="xs" c="dimmed">
                    Submitted: {r.submitted_at ? new Date(r.submitted_at).toLocaleDateString() : "Draft"}
                  </Text>
                </Stack>
              ),
            },
            {
              key: "category",
              header: "Category",
              render: (r) => (
                <Group gap="xs">
                  <Badge color="indigo" variant="light">
                    {r.category}
                  </Badge>
                  {r.half !== "full" && (
                    <Badge size="xs" color="gray">
                      {r.half}
                    </Badge>
                  )}
                </Group>
              ),
            },
            {
              key: "dates",
              header: "Duration",
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
              key: "status",
              header: "Stage",
              render: (r) => <StatusBadge status={r.status} />,
            },

            {
              key: "details",
              header: "Details / Notes",
              render: (r) => (
                <Stack gap={2}>
                  {r.unit_head_recommendation && (
                    <Badge size="xs" color="cyan">
                      Unit Head: {r.unit_head_recommendation}
                    </Badge>
                  )}
                  {r.substitute_id && (
                    <Badge size="xs" color="green">
                      Sub: #{r.substitute_id} (Accepted)
                    </Badge>
                  )}
                  <Text size="xs" c="dimmed" lineClamp={2}>
                    {r.purpose || "No reason given"}
                  </Text>
                </Stack>
              ),
            },
            {
              key: "actions",
              header: "Action",
              render: (r) => {
                if (r.status === "awaiting_unit_head") {
                  const isDirect = ["CL", "RH"].includes(r.category);
                  return isDirect ? (
                    <Group gap="xs">
                      <Button
                        size="xs"
                        color="teal"
                        leftSection={<FaCheck />}
                        onClick={() => handleUnitHeadAction(r, "approve")}
                        loading={unitHeadReviewMutation.isPending}
                      >
                        Approve
                      </Button>
                      <Button
                        size="xs"
                        color="red"
                        variant="light"
                        leftSection={<FaTimes />}
                        onClick={() => setActiveItem({ item: r, type: "uh_cl" })}
                      >
                        Reject
                      </Button>
                    </Group>
                  ) : (
                    <Group gap="xs">
                      <Button
                        size="xs"
                        color="indigo"
                        leftSection={<FaThumbsUp />}
                        onClick={() => handleUnitHeadAction(r, "recommend")}
                        loading={unitHeadReviewMutation.isPending}
                      >
                        Recommend
                      </Button>
                      <Button
                        size="xs"
                        color="orange"
                        variant="light"
                        onClick={() => handleUnitHeadAction(r, "not_recommend")}
                        loading={unitHeadReviewMutation.isPending}
                      >
                        Not Recommend
                      </Button>
                    </Group>
                  );
                }

                if (r.status === "awaiting_sanction") {
                  return (
                    <Group gap="xs">
                      <Button
                        size="xs"
                        color="teal"
                        leftSection={<FaCheck />}
                        onClick={() => handleSanctionAction(r, true)}
                        loading={sanctionMutation.isPending}
                      >
                        Sanction
                      </Button>
                      <Button
                        size="xs"
                        color="red"
                        variant="light"
                        leftSection={<FaTimes />}
                        onClick={() => setActiveItem({ item: r, type: "sanction" })}
                      >
                        Reject
                      </Button>
                    </Group>
                  );
                }

                if (r.status === "cancel_requested") {
                  return (
                    <Group gap="xs">
                      <Button
                        size="xs"
                        color="red"
                        onClick={() => handleCancelDecision(r, true)}
                        loading={cancelDecisionMutation.isPending}
                      >
                        Confirm Cancel
                      </Button>
                      <Button
                        size="xs"
                        variant="default"
                        onClick={() => handleCancelDecision(r, false)}
                        loading={cancelDecisionMutation.isPending}
                      >
                        Decline
                      </Button>
                    </Group>
                  );
                }

                if (r.status === "extension_requested") {
                  return (
                    <Group gap="xs">
                      <Button
                        size="xs"
                        color="teal"
                        onClick={() => handleExtensionDecision(r, true)}
                        loading={extensionDecisionMutation.isPending}
                      >
                        Approve Ext
                      </Button>
                      <Button
                        size="xs"
                        color="red"
                        variant="light"
                        onClick={() => handleExtensionDecision(r, false)}
                        loading={extensionDecisionMutation.isPending}
                      >
                        Reject Ext
                      </Button>
                    </Group>
                  );
                }

                if (r.status === "resumption_submitted") {
                  return (
                    <Button
                      size="xs"
                      color="cyan"
                      onClick={() => handleResumptionReview(r)}
                      loading={resumptionReviewMutation.isPending}
                    >
                      Verify Resumption
                    </Button>
                  );
                }

                return null;
              },
            },
          ]}
        />
      </Card>

      {/* Decision / Rejection Modal */}
      <Modal
        opened={Boolean(activeItem)}
        onClose={() => setActiveItem(null)}
        title={`Review Decision for Leave #${activeItem?.item?.id}`}
      >
        <Stack gap="md">
          <Text size="sm">
            Please enter remarks / justification for this decision:
          </Text>
          <Textarea
            label="Reason / Remarks"
            placeholder="Justification"
            value={decisionReason}
            onChange={(e) => setDecisionReason(e.currentTarget.value)}
            required
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setActiveItem(null)}>
              Cancel
            </Button>
            {activeItem?.type === "uh_cl" && (
              <Button
                color="red"
                onClick={() => activeItem && handleUnitHeadAction(activeItem.item, "reject")}
                loading={unitHeadReviewMutation.isPending}
              >
                Confirm Rejection
              </Button>
            )}
            {activeItem?.type === "sanction" && (
              <Button
                color="red"
                onClick={() => activeItem && handleSanctionAction(activeItem.item, false)}
                loading={sanctionMutation.isPending}
              >
                Confirm Rejection
              </Button>
            )}
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
