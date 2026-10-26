import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  Radio,
  Select,
  Stack,
  Tabs,
  Text,
  Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  FaCheck,
  FaClipboardCheck,
  FaRegCheckCircle,
  FaTimes,
  FaUserClock,
} from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useLeaveApplications,
  useRespondToSubstitute,
  useReviewCancellation,
  useReviewLeaveApplication,
  useReviewResumption,
} from "../api/hooks";
import type { LeaveApplication } from "../api/types";

export default function LeaveApprovalsPage() {
  const [activeTab, setActiveTab] = useState<string | null>("approvals");

  const {
    data: approvals,
    isPending: approvalsLoading,
    error: approvalsError,
  } = useLeaveApplications({ queue: "approvals" });

  const {
    data: substituteRequests,
    isPending: substituteLoading,
    error: substituteError,
  } = useLeaveApplications({ queue: "substitute" });

  const reviewMutation = useReviewLeaveApplication();
  const subResponseMutation = useRespondToSubstitute();
  const cancelReviewMutation = useReviewCancellation();
  const resumptionReviewMutation = useReviewResumption();

  const [selectedApp, setSelectedApp] = useState<LeaveApplication | null>(null);
  const [reviewModalOpen, setReviewModalOpen] = useState(false);
  const [reviewAction, setReviewAction] = useState<"approve" | "reject" | "recommend">("approve");
  const [recommendation, setRecommendation] = useState<"RECOMMENDED" | "NOT_RECOMMENDED">("RECOMMENDED");
  const [remarks, setRemarks] = useState("");

  const [subModalOpen, setSubModalOpen] = useState(false);
  const [subAction, setSubAction] = useState<"accept" | "decline">("accept");

  const error = approvalsError || substituteError;
  if (error) {
    return (
      <Container size="xl" py="md">
        <ErrorState error={error} />
      </Container>
    );
  }

  function handleReviewSubmit() {
    if (!selectedApp) return;

    if (selectedApp.status === "CANCELLATION_REQUESTED") {
      cancelReviewMutation.mutate(
        {
          id: selectedApp.id,
          approval_action: reviewAction === "approve" ? "approve" : "reject",
          remarks,
        },
        {
          onSuccess: () => {
            notifications.show({
              color: "green",
              title: "Cancellation Reviewed",
              message: `Cancellation decision recorded for #${selectedApp.id}.`,
            });
            setReviewModalOpen(false);
          },
          onError: (err) => {
            notifications.show({
              color: "red",
              title: "Review Failed",
              message: errorMessage(err),
            });
          },
        }
      );
    } else if (selectedApp.resumption_status === "PENDING") {
      resumptionReviewMutation.mutate(
        {
          id: selectedApp.id,
          approval_action: reviewAction === "approve" ? "approve" : "reject",
          remarks,
        },
        {
          onSuccess: () => {
            notifications.show({
              color: "green",
              title: "Resumption Reviewed",
              message: `Resumption reviewed and leave balance adjusted.`,
            });
            setReviewModalOpen(false);
          },
          onError: (err) => {
            notifications.show({
              color: "red",
              title: "Review Failed",
              message: errorMessage(err),
            });
          },
        }
      );
    } else {
      reviewMutation.mutate(
        {
          id: selectedApp.id,
          review_action: reviewAction,
          recommendation: reviewAction === "recommend" ? recommendation : "",
          remarks,
        },
        {
          onSuccess: () => {
            notifications.show({
              color: "green",
              title: "Decision Recorded",
              message: `Leave application #${selectedApp.id} was processed successfully.`,
            });
            setReviewModalOpen(false);
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
  }

  function handleSubstituteSubmit() {
    if (!selectedApp) return;
    subResponseMutation.mutate(
      {
        id: selectedApp.id,
        response: subAction,
        remarks,
      },
      {
        onSuccess: () => {
          notifications.show({
            color: subAction === "accept" ? "green" : "gray",
            title: `Substitute Request ${subAction === "accept" ? "Accepted" : "Declined"}`,
            message: `Your response has been communicated for #${selectedApp.id}.`,
          });
          setSubModalOpen(false);
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

  const isHigherSanction = (app: LeaveApplication) =>
    ["SCL", "EL", "COL", "VL"].includes(app.leave_type_code);

  return (
    <Container size="xl" py="md">
      <PageHeader
        title="Leave Approvals & Workflows"
        subtitle="Manage pending reviews, higher sanction authorizations, and substitute coverage"
      />

      <Tabs value={activeTab} onChange={setActiveTab} mt="md">
        <Tabs.List>
          <Tabs.Tab value="approvals" leftSection={<FaClipboardCheck />}>
            Pending Approvals ({approvals?.length ?? 0})
          </Tabs.Tab>
          <Tabs.Tab value="substitute" leftSection={<FaUserClock />}>
            Substitute Requests ({substituteRequests?.length ?? 0})
          </Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="approvals" pt="md">
          <Card withBorder padding="lg" radius="md">
            <DataTable<LeaveApplication>
              rows={(approvals ?? []) as LeaveApplication[]}
              loading={approvalsLoading}
              rowKey={(r) => r.id}
              minWidth={850}
              empty={{
                title: "No pending leave approvals",
                description: "There are currently no leave applications awaiting your review or sanction.",
              }}
              columns={[
                {
                  key: "applicant",
                  header: "Applicant",
                  render: (r) => (
                    <Stack gap={0}>
                      <Text fw={600}>{r.applicant_id}</Text>
                      <Text size="xs" c="dimmed">
                        Application #{r.id}
                      </Text>
                    </Stack>
                  ),
                },
                {
                  key: "details",
                  header: "Category & Period",
                  render: (r) => (
                    <Stack gap={0}>
                      <Group gap="xs">
                        <Badge size="sm">{r.leave_type_code}</Badge>
                        <Text size="sm">{r.leave_type_name}</Text>
                      </Group>
                      <Text size="xs" c="dimmed">
                        {r.start_date} to {r.end_date} ({r.leave_days} days)
                      </Text>
                      {r.station_leave_required && (
                        <Badge size="xs" color="teal" variant="outline" mt="2px">
                          Station Leave: {r.station_address || "Yes"}
                        </Badge>
                      )}
                    </Stack>
                  ),
                },
                {
                  key: "purpose",
                  header: "Reason",
                  render: (r) => (
                    <Text size="sm" lineClamp={2}>
                      {r.reason}
                    </Text>
                  ),
                },
                {
                  key: "stage",
                  header: "Current Stage",
                  render: (r) => (
                    <Stack gap={0}>
                      <Badge color="blue" variant="light">
                        {r.status.replace(/_/g, " ")}
                      </Badge>
                      {r.resumption_status === "PENDING" && (
                        <Badge color="green" size="xs" mt="2px">
                          Resumption on {r.resumption_date}
                        </Badge>
                      )}
                    </Stack>
                  ),
                },
                {
                  key: "actions",
                  header: "Review",
                  render: (r) => (
                    <Button
                      size="xs"
                      leftSection={<FaRegCheckCircle />}
                      onClick={() => {
                        setSelectedApp(r);
                        setRemarks("");
                        if (r.status === "AWAITING_UNIT_HEAD" && isHigherSanction(r)) {
                          setReviewAction("recommend");
                        } else {
                          setReviewAction("approve");
                        }
                        setReviewModalOpen(true);
                      }}
                    >
                      Process
                    </Button>
                  ),
                },
              ]}
            />
          </Card>
        </Tabs.Panel>

        <Tabs.Panel value="substitute" pt="md">
          <Card withBorder padding="lg" radius="md">
            <DataTable<LeaveApplication>
              rows={(substituteRequests ?? []) as LeaveApplication[]}
              loading={substituteLoading}
              rowKey={(r) => r.id}
              minWidth={800}
              empty={{
                title: "No substitute requests",
                description: "No colleagues have requested your responsibility coverage at this time.",
              }}
              columns={[
                {
                  key: "applicant",
                  header: "Applicant Requiring Coverage",
                  render: (r) => (
                    <Stack gap={0}>
                      <Text fw={600}>{r.applicant_id}</Text>
                      <Text size="xs" c="dimmed">
                        Application #{r.id}
                      </Text>
                    </Stack>
                  ),
                },
                {
                  key: "period",
                  header: "Absence Duration",
                  render: (r) => (
                    <Stack gap={0}>
                      <Text size="sm">
                        {r.start_date} to {r.end_date}
                      </Text>
                      <Text size="xs" c="dimmed">
                        {r.leave_days} days ({r.leave_type_code})
                      </Text>
                    </Stack>
                  ),
                },
                {
                  key: "purpose",
                  header: "Reason for Leave",
                  render: (r) => (
                    <Text size="sm" lineClamp={2}>
                      {r.reason}
                    </Text>
                  ),
                },
                {
                  key: "actions",
                  header: "Your Response",
                  render: (r) => (
                    <Group gap="xs">
                      <Button
                        size="xs"
                        color="green"
                        leftSection={<FaCheck />}
                        onClick={() => {
                          setSelectedApp(r);
                          setSubAction("accept");
                          setRemarks("");
                          setSubModalOpen(true);
                        }}
                      >
                        Accept
                      </Button>
                      <Button
                        size="xs"
                        color="red"
                        variant="subtle"
                        leftSection={<FaTimes />}
                        onClick={() => {
                          setSelectedApp(r);
                          setSubAction("decline");
                          setRemarks("");
                          setSubModalOpen(true);
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
        </Tabs.Panel>
      </Tabs>

      <Modal
        opened={reviewModalOpen}
        onClose={() => setReviewModalOpen(false)}
        title={`Review Application #${selectedApp?.id} (${selectedApp?.applicant_id})`}
        size="md"
      >
        {selectedApp && (
          <Stack gap="md">
            <Card withBorder padding="sm">
              <Text size="sm">
                <strong>{selectedApp.leave_type_name}</strong>: {selectedApp.start_date} to {selectedApp.end_date} ({selectedApp.leave_days} days)
              </Text>
              <Text size="xs" c="dimmed" mt="4px">
                Reason: {selectedApp.reason}
              </Text>
              {selectedApp.unit_head_recommendation && (
                <Text size="xs" c="blue" mt="4px">
                  Unit Head Recommendation: <strong>{selectedApp.unit_head_recommendation}</strong> ({selectedApp.unit_head_remarks || "No remarks"})
                </Text>
              )}
            </Card>

            {selectedApp.status === "AWAITING_UNIT_HEAD" && isHigherSanction(selectedApp) ? (
              <Radio.Group
                value={reviewAction}
                onChange={(val) => setReviewAction(val as "approve" | "reject" | "recommend")}
                label="Unit Head Review Action"
                description="For SCL, EL, COL, and VL, Unit Head records recommendation for Sanctioning Authority."
              >
                <Stack mt="xs" gap="xs">
                  <Radio value="recommend" label="Forward with Recommendation" />
                  <Radio value="reject" label="Reject Application" />
                </Stack>
              </Radio.Group>
            ) : (
              <Radio.Group
                value={reviewAction}
                onChange={(val) => setReviewAction(val as "approve" | "reject")}
                label="Decision"
              >
                <Group mt="xs">
                  <Radio value="approve" label="Approve" />
                  <Radio value="reject" label="Reject" />
                </Group>
              </Radio.Group>
            )}

            {reviewAction === "recommend" && (
              <Select
                label="Recommendation"
                value={recommendation}
                onChange={(val) => setRecommendation((val as "RECOMMENDED" | "NOT_RECOMMENDED") ?? "RECOMMENDED")}
                data={[
                  { value: "RECOMMENDED", label: "Recommended" },
                  { value: "NOT_RECOMMENDED", label: "Not Recommended" },
                ]}
              />
            )}

            <Textarea
              label="Review Remarks"
              placeholder="Record your remarks or conditions..."
              value={remarks}
              onChange={(e) => setRemarks(e.currentTarget.value)}
            />

            <Group justify="flex-end">
              <Button variant="default" onClick={() => setReviewModalOpen(false)}>
                Cancel
              </Button>
              <Button
                color={reviewAction === "reject" ? "red" : "blue"}
                onClick={handleReviewSubmit}
                loading={
                  reviewMutation.isPending ||
                  cancelReviewMutation.isPending ||
                  resumptionReviewMutation.isPending
                }
              >
                Submit Decision
              </Button>
            </Group>
          </Stack>
        )}
      </Modal>

      <Modal
        opened={subModalOpen}
        onClose={() => setSubModalOpen(false)}
        title={`Respond to Substitute Request #${selectedApp?.id}`}
        size="md"
      >
        {selectedApp && (
          <Stack gap="md">
            <Text size="sm">
              Colleague <strong>{selectedApp.applicant_id}</strong> has nominated you as substitute for {selectedApp.leave_days} days of leave ({selectedApp.start_date} to {selectedApp.end_date}).
            </Text>
            <Radio.Group
              value={subAction}
              onChange={(val) => setSubAction(val as "accept" | "decline")}
              label="Your Response"
            >
              <Group mt="xs">
                <Radio value="accept" label="Accept Responsibility" />
                <Radio value="decline" label="Decline" />
              </Group>
            </Radio.Group>
            <Textarea
              label="Remarks"
              placeholder="Remarks for the applicant..."
              value={remarks}
              onChange={(e) => setRemarks(e.currentTarget.value)}
            />
            <Group justify="flex-end">
              <Button variant="default" onClick={() => setSubModalOpen(false)}>
                Cancel
              </Button>
              <Button
                color={subAction === "accept" ? "green" : "red"}
                onClick={handleSubstituteSubmit}
                loading={subResponseMutation.isPending}
              >
                Submit Response
              </Button>
            </Group>
          </Stack>
        )}
      </Modal>
    </Container>
  );
}
