import { useEffect, useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  Stack,
  Text,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { PageHeader } from "../../../ui/components/PageHeader";
import { leaveApi } from "../api/client";
import type { LeaveApplication } from "../api/types";

export default function ApprovalsPage() {
  const [loading, setLoading] = useState(true);
  const [queue, setQueue] = useState<LeaveApplication[]>([]);
  const [activeApp, setActiveApp] = useState<LeaveApplication | null>(null);
  const [remarks, setRemarks] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const fetchQueue = async () => {
    try {
      setLoading(true);
      const data = await leaveApi.getApprovalsQueue();
      setQueue(data);
    } catch (err) {
      notifications.show({ title: "Error", message: errorMessage(err), color: "red" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueue();
  }, []);

  const handleUnitHeadAction = async (recommended: boolean) => {
    if (!activeApp) return;
    try {
      setSubmitting(true);
      await leaveApi.unitHeadReview(activeApp.id, recommended, remarks);
      notifications.show({
        title: "Action Recorded",
        message: `Successfully recorded ${recommended ? "recommendation/approval" : "rejection"}.`,
        color: recommended ? "teal" : "red",
      });
      setActiveApp(null);
      setRemarks("");
      fetchQueue();
    } catch (err) {
      notifications.show({ title: "Error", message: errorMessage(err), color: "red" });
    } finally {
      setSubmitting(false);
    }
  };

  const handleSanctionAction = async (decision: "approved" | "rejected") => {
    if (!activeApp) return;
    try {
      setSubmitting(true);
      await leaveApi.sanctionDecision(activeApp.id, decision, remarks);
      notifications.show({
        title: "Sanction Decision",
        message: `Leave application #${activeApp.id} ${decision}.`,
        color: decision === "approved" ? "teal" : "red",
      });
      setActiveApp(null);
      setRemarks("");
      fetchQueue();
    } catch (err) {
      notifications.show({ title: "Error", message: errorMessage(err), color: "red" });
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancellationReview = async (decision: "approved" | "rejected") => {
    if (!activeApp) return;
    try {
      setSubmitting(true);
      await leaveApi.processCancellation(activeApp.id, decision, remarks);
      notifications.show({
        title: "Cancellation Reviewed",
        message: `Cancellation request ${decision}.`,
        color: "teal",
      });
      setActiveApp(null);
      setRemarks("");
      fetchQueue();
    } catch (err) {
      notifications.show({ title: "Error", message: errorMessage(err), color: "red" });
    } finally {
      setSubmitting(false);
    }
  };

  const handleResumptionReview = async () => {
    if (!activeApp) return;
    try {
      setSubmitting(true);
      await leaveApi.processResumption(activeApp.id, remarks);
      notifications.show({
        title: "Resumption Closed",
        message: "Resumption report reviewed and balance adjustments synchronized.",
        color: "teal",
      });
      setActiveApp(null);
      setRemarks("");
      fetchQueue();
    } catch (err) {
      notifications.show({ title: "Error", message: errorMessage(err), color: "red" });
    } finally {
      setSubmitting(false);
    }
  };

  const handleForward = async () => {
    if (!activeApp) return;
    try {
      setSubmitting(true);
      await leaveApi.forwardApproval(activeApp.id, remarks);
      notifications.show({ title: "Forwarded", message: "Request sent to the configured sanctioning authority.", color: "teal" });
      setActiveApp(null);
      setRemarks("");
      fetchQueue();
    } catch (err) {
      notifications.show({ title: "Error", message: errorMessage(err), color: "red" });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Container size="xl">
      <PageHeader
        title="Leave Approvals Queue"
        subtitle="Review, recommend, and sanction employee leave requests."
      />

      <Card padding="lg" shadow="sm" radius="md" withBorder>
        <DataTable<LeaveApplication>
          rows={queue}
          loading={loading}
          rowKey={(r) => r.id}
          empty={{ title: "No pending approvals", description: "You have reviewed all pending leave requests." }}
          columns={[
            { key: "id", header: "ID", render: (r) => `#${r.id}` },
            { key: "user", header: "Applicant", render: (r) => `User #${r.user_id}` },
            { key: "category", header: "Category", render: (r) => <Badge variant="light">{r.category}</Badge> },
            { key: "dates", header: "Dates", render: (r) => `${r.start_date} → ${r.end_date}` },
            { key: "days", header: "Days", render: (r) => `${r.days_count} d` },
            { key: "purpose", header: "Purpose", render: (r) => <Text size="sm" lineClamp={1}>{r.purpose}</Text> },
            {
              key: "status",
              header: "Current Stage",
              render: (r) => (
                <Badge color="blue">{r.status.replace(/_/g, " ").toUpperCase()}</Badge>
              ),
            },
            {
              key: "actions",
              header: "Actions",
              render: (r) => (
                <Button size="xs" onClick={() => setActiveApp(r)}>
                  Process
                </Button>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        opened={!!activeApp}
        onClose={() => setActiveApp(null)}
        title={`Process Leave Application #${activeApp?.id}`}
        size="lg"
      >
        {activeApp && (
          <Stack gap="md">
            <Text size="sm"><b>Category:</b> {activeApp.category}</Text>
            <Text size="sm"><b>Dates:</b> {activeApp.start_date} to {activeApp.end_date} ({activeApp.days_count} days)</Text>
            <Text size="sm"><b>Purpose:</b> {activeApp.purpose}</Text>
            {activeApp.cancellation_reason && (
              <Text size="sm" c="orange"><b>Cancellation Reason:</b> {activeApp.cancellation_reason}</Text>
            )}
            {activeApp.resumption_date && (
              <Text size="sm" c="teal"><b>Resumption Date:</b> {activeApp.resumption_date}</Text>
            )}

            <TextInput
              label="Review / Sanction Remarks"
              placeholder="Enter remarks..."
              value={remarks}
              onChange={(e) => setRemarks(e.currentTarget.value)}
            />

            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => setActiveApp(null)}>Cancel</Button>

              {["under_review", "extension_requested"].includes(activeApp.status) && !activeApp.unit_head_reviewed_at && ["CL", "RH"].includes(activeApp.category) && (
                <>
                  <Button color="red" variant="outline" loading={submitting} onClick={() => handleUnitHeadAction(false)}>
                    Reject (Unit Head Final)
                  </Button>
                  <Button color="teal" loading={submitting} onClick={() => handleUnitHeadAction(true)}>
                    Approve (Unit Head Final)
                  </Button>
                </>
              )}

              {["under_review", "extension_requested"].includes(activeApp.status) && !activeApp.unit_head_reviewed_at && !["CL", "RH"].includes(activeApp.category) && (
                <>
                  <Button color="orange" variant="outline" loading={submitting} onClick={() => handleUnitHeadAction(false)}>
                    Unit Head: Not Recommended
                  </Button>
                  <Button color="blue" variant="light" loading={submitting} onClick={() => handleUnitHeadAction(true)}>
                    Unit Head: Recommend
                  </Button>
                </>
              )}

              {activeApp.establishment_user_id && !activeApp.establishment_reviewed_at && (
                <Button color="blue" loading={submitting} onClick={handleForward}>Establishment: Forward</Button>
              )}
              {activeApp.unit_head_reviewed_at && (!activeApp.establishment_user_id || activeApp.establishment_reviewed_at) && ["under_review", "extension_requested"].includes(activeApp.status) && (
                <>
                  <Button color="teal" loading={submitting} onClick={() => handleSanctionAction("approved")}>Sanctioning Authority: Approve</Button>
                  <Button color="red" loading={submitting} onClick={() => handleSanctionAction("rejected")}>Sanctioning Authority: Reject</Button>
                </>
              )}

              {activeApp.status === "cancel_requested" && (
                <>
                  {!activeApp.unit_head_reviewed_at && ["CL", "RH"].includes(activeApp.category) ? (
                    <>
                      <Button color="red" variant="outline" loading={submitting} onClick={() => handleUnitHeadAction(false)}>Reject Cancellation</Button>
                      <Button color="teal" loading={submitting} onClick={() => handleUnitHeadAction(true)}>Approve Cancellation</Button>
                    </>
                  ) : !activeApp.unit_head_reviewed_at ? (
                    <>
                      <Button color="orange" variant="outline" loading={submitting} onClick={() => handleUnitHeadAction(false)}>Not Recommended</Button>
                      <Button color="blue" loading={submitting} onClick={() => handleUnitHeadAction(true)}>Recommend</Button>
                    </>
                  ) : !activeApp.establishment_user_id || activeApp.establishment_reviewed_at ? (
                    <>
                      <Button color="red" variant="outline" loading={submitting} onClick={() => handleCancellationReview("rejected")}>Reject Cancellation</Button>
                      <Button color="teal" loading={submitting} onClick={() => handleCancellationReview("approved")}>Approve Cancellation (Restore Balance)</Button>
                    </>
                  ) : null}
                </>
              )}

              {activeApp.status === "resumption_submitted" && (
                <Button color="teal" loading={submitting} onClick={handleResumptionReview}>
                  Approve Resumption & Synchronize Balance
                </Button>
              )}
            </Group>
          </Stack>
        )}
      </Modal>
    </Container>
  );
}
