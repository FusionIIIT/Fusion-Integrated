import { useState } from "react";
import {
  Alert,
  Box,
  Grid,
  Group,
  Radio,
  Stack,
  Text,
  Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaInfoCircle } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { FormModal } from "../../../ui/components/FormModal";
import {
  useRespondSubstitute,
  useReviewApproval,
  useReviewResumption,
  useSanctionApproval,
} from "../api/hooks";
import type { LeaveRequest, SubstituteNomination } from "../api/types";

export function SubstituteResponseModal({
  nomination,
  opened,
  onClose,
}: {
  nomination: SubstituteNomination | null;
  opened: boolean;
  onClose: () => void;
}) {
  const [decision, setDecision] = useState<"accepted" | "declined">("accepted");
  const [remarks, setRemarks] = useState("");
  const respond = useRespondSubstitute();

  if (!nomination) return null;
  const req = nomination.request;

  function handleSubmit() {
    if (!nomination) return;
    respond.mutate(
      {
        id: nomination.id,
        payload: {
          decision,
          remarks: remarks.trim(),
        },
      },
      {
        onSuccess: () => {
          notifications.show({
            color: decision === "accepted" ? "green" : "orange",
            title: decision === "accepted" ? "Nomination Accepted" : "Nomination Declined",
            message: `You have ${decision} responsibility coverage for Application #${req?.application_number}.`,
          });
          setRemarks("");
          onClose();
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Response Failed",
            message: errorMessage(err),
          });
        },
      }
    );
  }

  return (
    <FormModal
      opened={opened}
      onClose={onClose}
      title="Respond to Substitute Nomination"
      subtitle={`Application #${req?.application_number} (${req?.leave_type?.name})`}
      onSubmit={handleSubmit}
      submitLabel={decision === "accepted" ? "Confirm & Accept" : "Confirm & Decline"}
      submitting={respond.isPending}
      danger={decision === "declined"}
      error={respond.error}
    >
      <Stack gap="md">
        <PaperDetails request={req} />

        <Radio.Group
          value={decision}
          onChange={(val) => setDecision(val as "accepted" | "declined")}
          label="Your Decision"
          required
        >
          <Group mt="xs">
            <Radio
              value="accepted"
              label="Accept Responsibility Coverage"
              color="green"
            />
            <Radio
              value="declined"
              label="Decline Nomination"
              color="red"
            />
          </Group>
        </Radio.Group>

        <Textarea
          label="Remarks (Optional)"
          placeholder={decision === "accepted" ? "Any handover notes..." : "Reason for declining..."}
          value={remarks}
          onChange={(e) => setRemarks(e.currentTarget.value)}
        />
      </Stack>
    </FormModal>
  );
}

export function ReviewDecisionModal({
  request,
  opened,
  onClose,
}: {
  request: LeaveRequest | null;
  opened: boolean;
  onClose: () => void;
}) {
  // Determine if this is a recommendation or final approval
  // For CL and RH: unit head is final authority (approve/reject)
  // For EL, SCL, COL, VL: unit head recommends (recommend/not_recommend)
  const isFinalAuthorityType =
    request?.leave_type?.code === "CL" || request?.leave_type?.code === "RH";
  const isCancellation =
    request?.status === "cancellation_pending_unit_head";

  const defaultDecision =
    isFinalAuthorityType || isCancellation ? "approve" : "recommend";

  const [decision, setDecision] = useState<"approve" | "reject" | "recommend" | "not_recommend">(
    defaultDecision
  );
  const [remarks, setRemarks] = useState("");
  const review = useReviewApproval();

  if (!request) return null;

  function handleSubmit() {
    if (!request) return;
    review.mutate(
      {
        id: request.id,
        payload: {
          decision,
          remarks: remarks.trim(),
        },
      },
      {
        onSuccess: () => {
          notifications.show({
            color: "blue",
            title: "Review Decision Recorded",
            message: `Review recorded for Application #${request.application_number}.`,
          });
          setRemarks("");
          onClose();
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Review Error",
            message: errorMessage(err),
          });
        },
      }
    );
  }

  const isPositive = decision === "approve" || decision === "recommend";

  return (
    <FormModal
      opened={opened}
      onClose={onClose}
      title="Unit Head / Department Review"
      subtitle={`Application #${request.application_number} (${request.leave_type?.name})`}
      onSubmit={handleSubmit}
      submitLabel={`Submit ${isPositive ? "Approval / Recommendation" : "Rejection / Disapproval"}`}
      submitting={review.isPending}
      danger={!isPositive}
      error={review.error}
    >
      <Stack gap="md">
        <PaperDetails request={request} />

        <Radio.Group
          value={decision}
          onChange={(val) => setDecision(val as any)}
          label="Review Recommendation / Decision"
          required
        >
          <Group mt="xs">
            {isFinalAuthorityType || isCancellation ? (
              <>
                <Radio value="approve" label="Approve Request" color="green" />
                <Radio value="reject" label="Reject Request" color="red" />
              </>
            ) : (
              <>
                <Radio value="recommend" label="Recommend for Sanction" color="blue" />
                <Radio value="not_recommend" label="Do Not Recommend" color="orange" />
              </>
            )}
          </Group>
        </Radio.Group>

        <Textarea
          label="Reviewer Remarks"
          placeholder="State reason or conditions..."
          required={!isPositive}
          minRows={2}
          value={remarks}
          onChange={(e) => setRemarks(e.currentTarget.value)}
        />
      </Stack>
    </FormModal>
  );
}

export function SanctionDecisionModal({
  request,
  opened,
  onClose,
}: {
  request: LeaveRequest | null;
  opened: boolean;
  onClose: () => void;
}) {
  const [decision, setDecision] = useState<"approve" | "reject">("approve");
  const [remarks, setRemarks] = useState("");
  const sanction = useSanctionApproval();

  if (!request) return null;

  function handleSubmit() {
    if (!request) return;
    sanction.mutate(
      {
        id: request.id,
        payload: {
          decision,
          remarks: remarks.trim(),
        },
      },
      {
        onSuccess: () => {
          notifications.show({
            color: decision === "approve" ? "green" : "red",
            title: decision === "approve" ? "Leave Sanctioned" : "Leave Rejected",
            message: `Final sanction decision recorded for Application #${request.application_number}.`,
          });
          setRemarks("");
          onClose();
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Sanction Error",
            message: errorMessage(err),
          });
        },
      }
    );
  }

  return (
    <FormModal
      opened={opened}
      onClose={onClose}
      title="Sanctioning Authority Decision"
      subtitle={`Application #${request.application_number} (${request.leave_type?.name})`}
      onSubmit={handleSubmit}
      submitLabel={decision === "approve" ? "Sanction Leave" : "Reject Leave"}
      submitting={sanction.isPending}
      danger={decision === "reject"}
      error={sanction.error}
    >
      <Stack gap="md">
        <PaperDetails request={request} />

        {request.unit_head_recommendation && (
          <Alert color="blue" icon={<FaInfoCircle />} title="Unit Head Recommendation">
            <Text size="sm">
              Status: <strong>{request.unit_head_recommendation}</strong>
              {request.unit_head_remarks ? ` — ${request.unit_head_remarks}` : ""}
            </Text>
          </Alert>
        )}

        <Radio.Group
          value={decision}
          onChange={(val) => setDecision(val as "approve" | "reject")}
          label="Sanction Decision"
          required
        >
          <Group mt="xs">
            <Radio value="approve" label="Approve & Sanction Leave" color="green" />
            <Radio value="reject" label="Reject Leave Request" color="red" />
          </Group>
        </Radio.Group>

        <Textarea
          label="Sanction Remarks"
          placeholder="Remarks or conditions..."
          required={decision === "reject"}
          minRows={2}
          value={remarks}
          onChange={(e) => setRemarks(e.currentTarget.value)}
        />
      </Stack>
    </FormModal>
  );
}

export function ResumptionReviewModal({
  request,
  opened,
  onClose,
}: {
  request: LeaveRequest | null;
  opened: boolean;
  onClose: () => void;
}) {
  const [decision, setDecision] = useState<"approved" | "rejected">("approved");
  const [remarks, setRemarks] = useState("");
  const review = useReviewResumption();

  if (!request) return null;

  function handleSubmit() {
    if (!request) return;
    review.mutate(
      {
        id: request.id,
        payload: {
          decision,
          remarks: remarks.trim(),
        },
      },
      {
        onSuccess: () => {
          notifications.show({
            color: "teal",
            title: "Resumption Review Completed",
            message: `Duty resumption review completed for #${request.application_number}.`,
          });
          onClose();
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Review Error",
            message: errorMessage(err),
          });
        },
      }
    );
  }

  return (
    <FormModal
      opened={opened}
      onClose={onClose}
      title="Review Duty Resumption"
      subtitle={`Application #${request.application_number} (${request.leave_type?.name})`}
      onSubmit={handleSubmit}
      submitLabel="Complete Resumption Review"
      submitting={review.isPending}
      error={review.error}
    >
      <Stack gap="md">
        <PaperDetails request={request} />

        <Radio.Group
          value={decision}
          onChange={(val) => setDecision(val as "approved" | "rejected")}
          label="Resumption Verification"
          required
        >
          <Group mt="xs">
            <Radio value="approved" label="Approve Resumption & Balance Adjustment" color="green" />
            <Radio value="rejected" label="Reject Resumption Report" color="red" />
          </Group>
        </Radio.Group>

        <Textarea
          label="Review Remarks"
          placeholder="Verification observations..."
          value={remarks}
          onChange={(e) => setRemarks(e.currentTarget.value)}
        />
      </Stack>
    </FormModal>
  );
}

function PaperDetails({ request }: { request: LeaveRequest | null | undefined }) {
  if (!request) return null;
  return (
    <Box p="sm" style={{ background: "var(--mantine-color-gray-0)", borderRadius: 6 }}>
      <Grid>
        <Grid.Col span={6}>
          <Text size="xs" c="dimmed">Applicant User ID / Dept</Text>
          <Text size="sm" fw={600}>User #{request.user_id} ({request.department})</Text>
        </Grid.Col>
        <Grid.Col span={6}>
          <Text size="xs" c="dimmed">Leave Duration</Text>
          <Text size="sm" fw={600}>{request.start_date} to {request.end_date} ({request.requested_days} days)</Text>
        </Grid.Col>
        <Grid.Col span={12}>
          <Text size="xs" c="dimmed">Reason</Text>
          <Text size="xs">{request.reason}</Text>
        </Grid.Col>
      </Grid>
    </Box>
  );
}
