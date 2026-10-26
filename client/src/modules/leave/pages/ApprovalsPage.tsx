import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Select,
  Stack,
  Text,
} from "@mantine/core";
import {
  FaCheckDouble,
  FaClipboardCheck,
  FaEye,
  FaGavel,
  FaUserCheck,
} from "react-icons/fa";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useApprovalsQueue } from "../api/hooks";
import type { LeaveRequest } from "../api/types";
import {
  ResumptionReviewModal,
  ReviewDecisionModal,
  SanctionDecisionModal,
} from "../components/ApprovalModals";
import { LeaveDetailModal } from "../components/LeaveActionModals";
import { LeaveStatusBadge } from "../components/LeaveStatusBadge";

export default function ApprovalsPage() {
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [detailRequest, setDetailRequest] = useState<LeaveRequest | null>(null);
  const [reviewRequest, setReviewRequest] = useState<LeaveRequest | null>(null);
  const [sanctionRequest, setSanctionRequest] = useState<LeaveRequest | null>(null);
  const [resumptionRequest, setResumptionRequest] = useState<LeaveRequest | null>(null);

  const { data, isPending, error } = useApprovalsQueue(statusFilter ?? undefined);

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  const requests = data ?? [];

  function handleActionClick(r: LeaveRequest) {
    if (r.status === "resumption_review_pending") {
      setResumptionRequest(r);
    } else if (
      r.status === "awaiting_sanction" ||
      r.status === "cancellation_pending_sanction" ||
      r.status === "extension_pending_sanction"
    ) {
      setSanctionRequest(r);
    } else {
      setReviewRequest(r);
    }
  }

  return (
    <Container size="xl">
      <PageHeader
        title="Leave Approvals Queue"
        subtitle="Review, recommend, and sanction employee leave requests within your departmental and role authority."
      />

      <Card withBorder padding="lg" radius="md">
        <Group justify="space-between" mb="md" wrap="wrap">
          <div>
            <Text fw={700} size="md">
              Pending Authorization Queue
            </Text>
            <Text size="xs" c="dimmed">
              Requests displayed are strictly scoped to your authorized approval stages and department.
            </Text>
          </div>
          <Select
            size="xs"
            placeholder="Filter by workflow stage"
            clearable
            value={statusFilter}
            onChange={setStatusFilter}
            data={[
              { value: "awaiting_unit_head", label: "Unit Head Review Pending" },
              { value: "awaiting_sanction", label: "Sanction Pending" },
              { value: "cancellation_pending_unit_head", label: "Cancellation — Unit Head" },
              { value: "cancellation_pending_sanction", label: "Cancellation — Sanction" },
              { value: "awaiting_extension_unit_head", label: "Extension — Unit Head" },
              { value: "extension_pending_sanction", label: "Extension — Sanction" },
              { value: "resumption_review_pending", label: "Resumption Verification" },
            ]}
          />
        </Group>

        <DataTable<LeaveRequest>
          rows={requests}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={900}
          columns={[
            {
              key: "applicant",
              header: "Applicant / Dept",
              render: (r) => (
                <Stack gap={0}>
                  <Text fw={600} size="sm">
                    User #{r.user_id}
                  </Text>
                  <Text size="xs" c="dimmed">
                    {r.department} • {r.cadre}
                  </Text>
                </Stack>
              ),
            },
            {
              key: "application",
              header: "Application #",
              render: (r) => (
                <Stack gap={0}>
                  <Text fw={600} size="sm">
                    {r.application_number}
                  </Text>
                  <Text size="xs" c="dimmed">
                    {r.leave_type?.name} ({r.leave_type?.code})
                  </Text>
                </Stack>
              ),
            },
            {
              key: "period",
              header: "Duration",
              render: (r) => (
                <Stack gap={0}>
                  <Text size="sm">
                    {r.start_date} → {r.end_date}
                  </Text>
                  <Group gap={4}>
                    <Text size="xs" c="dimmed">
                      {r.requested_days} days
                    </Text>
                    {r.is_half_day && (
                      <Badge size="xs" color="blue" variant="outline">
                        Half Day
                      </Badge>
                    )}
                    {r.is_station_leave && (
                      <Badge size="xs" color="gray" variant="outline">
                        Station Leave
                      </Badge>
                    )}
                  </Group>
                </Stack>
              ),
            },
            {
              key: "stage",
              header: "Stage / Status",
              render: (r) => (
                <Stack gap={2}>
                  <LeaveStatusBadge status={r.status} />
                  <Text size="xs" c="dimmed">
                    Role: {r.current_handler_role || "Competent Authority"}
                  </Text>
                </Stack>
              ),
            },
            {
              key: "actions",
              header: "Action",
              align: "right",
              render: (r) => {
                const isSanctionStage =
                  r.status === "awaiting_sanction" ||
                  r.status === "cancellation_pending_sanction" ||
                  r.status === "extension_pending_sanction";

                const isResumptionStage = r.status === "resumption_review_pending";

                return (
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
                      color={isSanctionStage ? "indigo" : isResumptionStage ? "teal" : "blue"}
                      leftSection={
                        isSanctionStage ? (
                          <FaGavel size={12} />
                        ) : isResumptionStage ? (
                          <FaClipboardCheck size={12} />
                        ) : (
                          <FaCheckDouble size={12} />
                        )
                      }
                      onClick={() => handleActionClick(r)}
                    >
                      {isSanctionStage ? "Sanction" : isResumptionStage ? "Verify" : "Review"}
                    </Button>
                  </Group>
                );
              },
            },
          ]}
          empty={{
            icon: FaUserCheck,
            title: "Approvals queue is clear",
            description: "There are no pending leave requests awaiting your recommendation or sanction at this time.",
          }}
        />
      </Card>

      {/* Detail Inspection Modal */}
      <LeaveDetailModal
        request={detailRequest}
        opened={detailRequest !== null}
        onClose={() => setDetailRequest(null)}
      />

      {/* Unit Head Review / Recommendation Modal */}
      <ReviewDecisionModal
        request={reviewRequest}
        opened={reviewRequest !== null}
        onClose={() => setReviewRequest(null)}
      />

      {/* Final Sanction Modal */}
      <SanctionDecisionModal
        request={sanctionRequest}
        opened={sanctionRequest !== null}
        onClose={() => setSanctionRequest(null)}
      />

      {/* Resumption Review Modal */}
      <ResumptionReviewModal
        request={resumptionRequest}
        opened={resumptionRequest !== null}
        onClose={() => setResumptionRequest(null)}
      />
    </Container>
  );
}
