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
import { FaClipboardCheck, FaEye, FaUndo } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useApprovalsQueue, useLeaveRequests } from "../api/hooks";
import type { LeaveRequest } from "../api/types";
import { ResumptionReviewModal } from "../components/ApprovalModals";
import { LeaveDetailModal, ResumeLeaveModal } from "../components/LeaveActionModals";
import { LeaveStatusBadge } from "../components/LeaveStatusBadge";

export default function ResumptionsPage() {
  const { can } = useAuth();
  const canApprove = can("leave.request.approve");

  const [activeTab, setActiveTab] = useState<"mine" | "approvals">(
    canApprove ? "approvals" : "mine"
  );
  const [detailRequest, setDetailRequest] = useState<LeaveRequest | null>(null);
  const [resumeRequest, setResumeRequest] = useState<LeaveRequest | null>(null);
  const [reviewRequest, setReviewRequest] = useState<LeaveRequest | null>(null);

  // My leave requests that may need resumption
  const {
    data: myRequests,
    isPending: myRequestsLoading,
    error: myRequestsError,
  } = useLeaveRequests();

  // Approver queue filtered to resumption_review_pending
  const {
    data: pendingApprovals,
    isPending: approvalsLoading,
    error: approvalsError,
  } = useApprovalsQueue("resumption_review_pending");

  if (myRequestsError || approvalsError) {
    return (
      <Container size="xl">
        <ErrorState error={myRequestsError || approvalsError} />
      </Container>
    );
  }

  // Filter my requests: leaves of category EL, COL, VL that are approved, extended, or resumption pending
  const myResumptionEligible = (myRequests ?? []).filter(
    (r) =>
      ["EL", "COL", "VL"].includes(r.leave_type?.code) &&
      [
        "approved",
        "extended",
        "resumption_review_pending",
        "resumption_reviewed_no_adjustment",
        "resumption_reviewed_early_synchronized",
        "resumption_reviewed_late_synchronized",
      ].includes(r.status)
  );

  return (
    <Container size="xl">
      <PageHeader
        title="Duty Resumptions"
        subtitle="Report duty resumption upon return from Earned Leave, Commuted Leave, or Vacation Leave, and review returning staff."
      />

      <Card withBorder padding="lg" radius="md">
        {canApprove && (
          <Group justify="space-between" mb="lg">
            <Text fw={700} size="md">
              Resumption Hub
            </Text>
            <SegmentedControl
              size="xs"
              value={activeTab}
              onChange={(val) => setActiveTab(val as "mine" | "approvals")}
              data={[
                {
                  value: "approvals",
                  label: `Review Queue (${(pendingApprovals ?? []).length})`,
                },
                {
                  value: "mine",
                  label: `My Resumptions (${myResumptionEligible.length})`,
                },
              ]}
            />
          </Group>
        )}

        {/* Tab 1: Approver Queue */}
        {activeTab === "approvals" && (
          <Stack gap="md">
            <Text size="sm" c="dimmed">
              Duty resumptions submitted by faculty and staff awaiting your verification and balance reconciliation.
            </Text>

            <DataTable<LeaveRequest>
              rows={(pendingApprovals ?? []) as LeaveRequest[]}
              loading={approvalsLoading}
              rowKey={(r) => r.id}
              minWidth={850}
              columns={[
                {
                  key: "applicant",
                  header: "Employee / Dept",
                  render: (r) => (
                    <Stack gap={0}>
                      <Text fw={600} size="sm">
                        User #{r.user_id}
                      </Text>
                      <Text size="xs" c="dimmed">
                        {r.department} • Application #{r.application_number}
                      </Text>
                    </Stack>
                  ),
                },
                {
                  key: "leave_type",
                  header: "Category",
                  render: (r) => (
                    <Text size="sm">
                      {r.leave_type?.name} ({r.leave_type?.code})
                    </Text>
                  ),
                },
                {
                  key: "dates",
                  header: "Approved Period",
                  render: (r) => (
                    <Stack gap={0}>
                      <Text size="sm">
                        {r.start_date} → {r.end_date}
                      </Text>
                      <Text size="xs" c="dimmed">
                        {r.requested_days} days
                      </Text>
                    </Stack>
                  ),
                },
                {
                  key: "status",
                  header: "Status",
                  render: (r) => <LeaveStatusBadge status={r.status} />,
                },
                {
                  key: "actions",
                  header: "Actions",
                  align: "right",
                  render: (r) => (
                    <Group justify="flex-end" gap="xs">
                      <Button
                        size="xs"
                        variant="subtle"
                        leftSection={<FaEye size={12} />}
                        onClick={() => setDetailRequest(r)}
                      >
                        Inspect
                      </Button>
                      <Button
                        size="xs"
                        color="teal"
                        leftSection={<FaClipboardCheck size={12} />}
                        onClick={() => setReviewRequest(r)}
                      >
                        Verify Resumption
                      </Button>
                    </Group>
                  ),
                },
              ]}
              empty={{
                icon: FaClipboardCheck,
                title: "No resumptions awaiting review",
                description: "All duty resumption reports have been processed.",
              }}
            />
          </Stack>
        )}

        {/* Tab 2: My Resumptions */}
        {activeTab === "mine" && (
          <Stack gap="md">
            <Text size="sm" c="dimmed">
              Submit your actual duty return date following approved EL, COL, or VL leave.
            </Text>

            <DataTable<LeaveRequest>
              rows={myResumptionEligible}
              loading={myRequestsLoading}
              rowKey={(r) => r.id}
              minWidth={850}
              columns={[
                {
                  key: "application",
                  header: "Application #",
                  render: (r) => (
                    <Stack gap={0}>
                      <Text fw={600} size="sm">
                        #{r.application_number}
                      </Text>
                      <Text size="xs" c="dimmed">
                        {r.leave_type?.name} ({r.leave_type?.code})
                      </Text>
                    </Stack>
                  ),
                },
                {
                  key: "period",
                  header: "Approved Leave Dates",
                  render: (r) => (
                    <Stack gap={0}>
                      <Text size="sm">
                        {r.start_date} → {r.end_date}
                      </Text>
                      <Text size="xs" c="dimmed">
                        {r.requested_days} days sanctioned
                      </Text>
                    </Stack>
                  ),
                },
                {
                  key: "status",
                  header: "Resumption State",
                  render: (r) => <LeaveStatusBadge status={r.status} />,
                },
                {
                  key: "actions",
                  header: "Action",
                  align: "right",
                  render: (r) => {
                    const isPendingReview = r.status === "resumption_review_pending";
                    const isCompleted =
                      r.status === "resumption_reviewed_no_adjustment" ||
                      r.status === "resumption_reviewed_early_synchronized" ||
                      r.status === "resumption_reviewed_late_synchronized";

                    return (
                      <Group justify="flex-end" gap="xs">
                        <Button
                          size="xs"
                          variant="subtle"
                          leftSection={<FaEye size={12} />}
                          onClick={() => setDetailRequest(r)}
                        >
                          Details
                        </Button>
                        {!isPendingReview && !isCompleted ? (
                          <Button
                            size="xs"
                            color="blue"
                            leftSection={<FaUndo size={12} />}
                            onClick={() => setResumeRequest(r)}
                          >
                            Submit Resumption
                          </Button>
                        ) : (
                          <Badge variant="outline" color={isCompleted ? "green" : "violet"}>
                            {isCompleted ? "Verified & Reconciled" : "Review in Progress"}
                          </Badge>
                        )}
                      </Group>
                    );
                  },
                },
              ]}
              empty={{
                icon: FaUndo,
                title: "No leaves requiring duty resumption",
                description: "Only ongoing or completed EL, COL, and VL leaves require resumption reports.",
              }}
            />
          </Stack>
        )}
      </Card>

      {/* Modals */}
      <LeaveDetailModal
        request={detailRequest}
        opened={detailRequest !== null}
        onClose={() => setDetailRequest(null)}
      />

      <ResumeLeaveModal
        request={resumeRequest}
        opened={resumeRequest !== null}
        onClose={() => setResumeRequest(null)}
      />

      <ResumptionReviewModal
        request={reviewRequest}
        opened={reviewRequest !== null}
        onClose={() => setReviewRequest(null)}
      />
    </Container>
  );
}
