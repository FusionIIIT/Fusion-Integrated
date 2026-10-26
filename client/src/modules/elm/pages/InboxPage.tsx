import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  Stack,
  Tabs,
  Text,
  Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  FaCheck,
  FaCheckCircle,
  FaClock,
  FaHandshake,
  FaInbox,
  FaTimes,
  FaUndo,
} from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import {
  useDecide,
  useDecideCancellation,
  useInbox,
  useRecommend,
  useReviewResumption,
  useSubstituteInbox,
  useSubstituteRespond,
} from "../api/hooks";
import {
  CATEGORY_LABELS,
  STATUS_LABELS,
  type LeaveApplication,
} from "../api/types";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";

export default function InboxPage() {
  const { data: inboxData, isPending: inboxPending, error: inboxError } = useInbox();
  const {
    data: subData,
    isPending: subPending,
    error: subError,
  } = useSubstituteInbox();

  const decide = useDecide();
  const recommend = useRecommend();
  const decideCancel = useDecideCancellation();
  const reviewResumption = useReviewResumption();
  const substituteRespond = useSubstituteRespond();

  // Action modal states
  const [decideModalApp, setDecideModalApp] = useState<{
    app: LeaveApplication;
    approve: boolean;
  } | null>(null);
  const [decisionNote, setDecisionNote] = useState("");

  const [recommendModalApp, setRecommendModalApp] = useState<{
    app: LeaveApplication;
    recommended: boolean;
  } | null>(null);
  const [recommendNote, setRecommendNote] = useState("");

  const [cancelModalApp, setCancelModalApp] = useState<{
    app: LeaveApplication;
    approve: boolean;
  } | null>(null);
  const [cancelDecisionNote, setCancelDecisionNote] = useState("");

  const [resumptionModalApp, setResumptionModalApp] = useState<LeaveApplication | null>(null);
  const [resumptionReviewNote, setResumptionReviewNote] = useState("");

  if (inboxError) return <Container size="xl"><ErrorState error={inboxError} /></Container>;
  if (subError) return <Container size="xl"><ErrorState error={subError} /></Container>;

  const applications = inboxData?.results ?? [];
  const substituteRequests = subData?.results ?? [];

  // Categorize inbox items by workflow stage
  const pendingDecisions = applications.filter((a) =>
    ["submitted", "forwarded"].includes(a.status),
  );
  const pendingCancellations = applications.filter(
    (a) => a.status === "cancel_req",
  );
  const pendingResumptions = applications.filter(
    (a) => a.status === "res_req",
  );

  function handleDecideSubmit() {
    if (!decideModalApp) return;
    decide.mutate(
      {
        id: decideModalApp.app.id,
        approve: decideModalApp.approve,
        note: decisionNote,
      },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: decideModalApp.approve ? "Leave Sanctioned" : "Leave Rejected",
            message: `Decision recorded for Application #${decideModalApp.app.id}.`,
          });
          setDecideModalApp(null);
          setDecisionNote("");
        },
        onError: (e) =>
          notifications.show({
            color: "red",
            title: "Decision Failed",
            message: errorMessage(e),
          }),
      },
    );
  }

  function handleRecommendSubmit() {
    if (!recommendModalApp) return;
    recommend.mutate(
      {
        id: recommendModalApp.app.id,
        recommended: recommendModalApp.recommended,
        note: recommendNote,
      },
      {
        onSuccess: () => {
          notifications.show({
            color: "blue",
            title: recommendModalApp.recommended ? "Recommended" : "Not Recommended",
            message: `Recommendation forwarded for Application #${recommendModalApp.app.id}.`,
          });
          setRecommendModalApp(null);
          setRecommendNote("");
        },
        onError: (e) =>
          notifications.show({
            color: "red",
            title: "Recommendation Failed",
            message: errorMessage(e),
          }),
      },
    );
  }

  function handleCancelDecisionSubmit() {
    if (!cancelModalApp) return;
    decideCancel.mutate(
      {
        id: cancelModalApp.app.id,
        approve: cancelModalApp.approve,
        note: cancelDecisionNote,
      },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: cancelModalApp.approve ? "Cancellation Sanctioned" : "Cancellation Rejected",
            message: `Cancellation decision updated for Application #${cancelModalApp.app.id}.`,
          });
          setCancelModalApp(null);
          setCancelDecisionNote("");
        },
        onError: (e) =>
          notifications.show({
            color: "red",
            title: "Action Failed",
            message: errorMessage(e),
          }),
      },
    );
  }

  function handleResumptionReviewSubmit() {
    if (!resumptionModalApp) return;
    reviewResumption.mutate(
      { id: resumptionModalApp.id, note: resumptionReviewNote },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Resumption Verified",
            message: `Duty return verified and balances reconciled for #${resumptionModalApp.id}.`,
          });
          setResumptionModalApp(null);
          setResumptionReviewNote("");
        },
        onError: (e) =>
          notifications.show({
            color: "red",
            title: "Resumption Review Failed",
            message: errorMessage(e),
          }),
      },
    );
  }

  function handleSubstituteResponse(id: number, accept: boolean) {
    substituteRespond.mutate(
      { id, accept },
      {
        onSuccess: () =>
          notifications.show({
            color: accept ? "green" : "orange",
            title: accept ? "Nomination Accepted" : "Nomination Declined",
            message: "Response recorded.",
          }),
        onError: (e) =>
          notifications.show({
            color: "red",
            title: "Could not respond",
            message: errorMessage(e),
          }),
      },
    );
  }

  return (
    <Container size="xl">
      <PageHeader
        title="Leave Inbox"
        subtitle="Sanctioning, recommendation, cancellation, and responsibility coverage requests"
      />

      <Tabs defaultValue="decisions">
        <Tabs.List mb="md">
          <Tabs.Tab
            value="decisions"
            leftSection={<FaCheckCircle size={14} />}
            rightSection={
              pendingDecisions.length > 0 ? (
                <Badge size="xs" circle color="blue">
                  {pendingDecisions.length}
                </Badge>
              ) : null
            }
          >
            Leave Approvals
          </Tabs.Tab>

          <Tabs.Tab
            value="cancellations"
            leftSection={<FaUndo size={14} />}
            rightSection={
              pendingCancellations.length > 0 ? (
                <Badge size="xs" circle color="orange">
                  {pendingCancellations.length}
                </Badge>
              ) : null
            }
          >
            Cancellations
          </Tabs.Tab>

          <Tabs.Tab
            value="resumptions"
            leftSection={<FaClock size={14} />}
            rightSection={
              pendingResumptions.length > 0 ? (
                <Badge size="xs" circle color="teal">
                  {pendingResumptions.length}
                </Badge>
              ) : null
            }
          >
            Duty Resumptions
          </Tabs.Tab>

          <Tabs.Tab
            value="substitute"
            leftSection={<FaHandshake size={14} />}
            rightSection={
              substituteRequests.length > 0 ? (
                <Badge size="xs" circle color="yellow">
                  {substituteRequests.length}
                </Badge>
              ) : null
            }
          >
            Substitute Coverage
          </Tabs.Tab>
        </Tabs.List>

        {/* Tab 1: Direct Decisions & Recommendations */}
        <Tabs.Panel value="decisions">
          <Card padding="lg">
            <DataTable<LeaveApplication>
              rows={pendingDecisions}
              loading={inboxPending}
              rowKey={(r) => r.id}
              columns={[
                {
                  key: "applicant",
                  header: "Applicant & Dept",
                  render: (r) => (
                    <Stack gap={2}>
                      <Text fw={600}>User #{r.user_id}</Text>
                      <Text size="xs" c="dimmed">
                        {r.department || "Institute General"}
                      </Text>
                    </Stack>
                  ),
                },
                {
                  key: "category",
                  header: "Leave Type",
                  render: (r) => (
                    <Stack gap={2}>
                      <Text size="sm">{CATEGORY_LABELS[r.category]}</Text>
                      <Text size="xs" c="dimmed">
                        {r.half !== "full" ? `(${r.half.replace("_", " ")})` : "Full Day"}
                      </Text>
                    </Stack>
                  ),
                },
                {
                  key: "period",
                  header: "Period & Days",
                  render: (r) => (
                    <Stack gap={2}>
                      <Text size="sm">
                        {r.start_date} — {r.end_date}
                      </Text>
                      <Badge size="xs" variant="outline">
                        {r.chargeable_days} day(s)
                      </Badge>
                    </Stack>
                  ),
                },
                {
                  key: "status",
                  header: "Stage",
                  render: (r) => (
                    <Stack gap={2}>
                      <Badge
                        color={r.status === "forwarded" ? "blue" : "yellow"}
                        variant="light"
                      >
                        {STATUS_LABELS[r.status] ?? r.status}
                      </Badge>
                      {r.recommendation_note && (
                        <Text size="xs" c="dimmed">
                          Rec: {r.recommendation_note}
                        </Text>
                      )}
                    </Stack>
                  ),
                },
                {
                  key: "purpose",
                  header: "Purpose",
                  render: (r) => (
                    <Text size="xs" lineClamp={2}>
                      {r.purpose || "—"}
                    </Text>
                  ),
                },
                {
                  key: "actions",
                  header: "Action",
                  align: "right",
                  render: (r) => {
                    const isHigherSanction = ["scl", "el", "col", "vl"].includes(r.category);
                    const canRecommend = isHigherSanction && r.status === "submitted";

                    return (
                      <Group justify="flex-end" gap="xs">
                        {canRecommend && (
                          <>
                            <Button
                              size="xs"
                              color="blue"
                              variant="light"
                              onClick={() =>
                                setRecommendModalApp({ app: r, recommended: true })
                              }
                            >
                              Recommend
                            </Button>
                            <Button
                              size="xs"
                              color="orange"
                              variant="subtle"
                              onClick={() =>
                                setRecommendModalApp({ app: r, recommended: false })
                              }
                            >
                              Do Not Recommend
                            </Button>
                          </>
                        )}
                        <Button
                          size="xs"
                          color="green"
                          onClick={() => setDecideModalApp({ app: r, approve: true })}
                        >
                          Approve
                        </Button>
                        <Button
                          size="xs"
                          color="red"
                          variant="light"
                          onClick={() => setDecideModalApp({ app: r, approve: false })}
                        >
                          Reject
                        </Button>
                      </Group>
                    );
                  },
                },
              ]}
              empty={{
                icon: FaInbox,
                title: "No pending approval requests",
                description: "All leave applications within your scope have been decided.",
              }}
            />
          </Card>
        </Tabs.Panel>

        {/* Tab 2: Cancellation Requests */}
        <Tabs.Panel value="cancellations">
          <Card padding="lg">
            <DataTable<LeaveApplication>
              rows={pendingCancellations}
              loading={inboxPending}
              rowKey={(r) => r.id}
              columns={[
                {
                  key: "applicant",
                  header: "Applicant",
                  render: (r) => <Text fw={600}>User #{r.user_id}</Text>,
                },
                {
                  key: "category",
                  header: "Type",
                  render: (r) => CATEGORY_LABELS[r.category],
                },
                {
                  key: "period",
                  header: "Approved Period",
                  render: (r) => `${r.start_date} — ${r.end_date} (${r.chargeable_days} days)`,
                },
                {
                  key: "actions",
                  header: "Cancellation Decision",
                  align: "right",
                  render: (r) => (
                    <Group justify="flex-end" gap="xs">
                      <Button
                        size="xs"
                        color="red"
                        onClick={() => setCancelModalApp({ app: r, approve: true })}
                      >
                        Approve Cancellation
                      </Button>
                      <Button
                        size="xs"
                        variant="default"
                        onClick={() => setCancelModalApp({ app: r, approve: false })}
                      >
                        Keep Leave Active
                      </Button>
                    </Group>
                  ),
                },
              ]}
              empty={{
                icon: FaUndo,
                title: "No pending cancellation requests",
                description: "No approved leaves are currently awaiting cancellation sanction.",
              }}
            />
          </Card>
        </Tabs.Panel>

        {/* Tab 3: Duty Resumptions */}
        <Tabs.Panel value="resumptions">
          <Card padding="lg">
            <DataTable<LeaveApplication>
              rows={pendingResumptions}
              loading={inboxPending}
              rowKey={(r) => r.id}
              columns={[
                {
                  key: "applicant",
                  header: "Applicant",
                  render: (r) => <Text fw={600}>User #{r.user_id}</Text>,
                },
                {
                  key: "category",
                  header: "Leave",
                  render: (r) => CATEGORY_LABELS[r.category],
                },
                {
                  key: "dates",
                  header: "Approved Period",
                  render: (r) => `${r.start_date} to ${r.end_date}`,
                },
                {
                  key: "actual",
                  header: "Reported Resumption Date",
                  render: (r) => (
                    <Stack gap={2}>
                      <Badge color="teal">{r.actual_resumption_date}</Badge>
                      {r.resumption_note && (
                        <Text size="xs" c="dimmed">
                          {r.resumption_note}
                        </Text>
                      )}
                    </Stack>
                  ),
                },
                {
                  key: "actions",
                  header: "Action",
                  align: "right",
                  render: (r) => (
                    <Group justify="flex-end">
                      <Button
                        size="xs"
                        color="teal"
                        onClick={() => setResumptionModalApp(r)}
                      >
                        Verify & Reconcile
                      </Button>
                    </Group>
                  ),
                },
              ]}
              empty={{
                icon: FaClock,
                title: "No duty resumptions pending",
                description: "No return-to-duty reports are waiting for verification.",
              }}
            />
          </Card>
        </Tabs.Panel>

        {/* Tab 4: Substitute Requests */}
        <Tabs.Panel value="substitute">
          <Card padding="lg">
            <DataTable<LeaveApplication>
              rows={substituteRequests}
              loading={subPending}
              rowKey={(r) => r.id}
              columns={[
                {
                  key: "applicant",
                  header: "Colleague (Applicant)",
                  render: (r) => <Text fw={600}>User #{r.user_id}</Text>,
                },
                {
                  key: "category",
                  header: "Leave Type",
                  render: (r) => CATEGORY_LABELS[r.category],
                },
                {
                  key: "period",
                  header: "Period of Absence",
                  render: (r) => `${r.start_date} — ${r.end_date}`,
                },
                {
                  key: "purpose",
                  header: "Purpose / Note",
                  render: (r) => <Text size="xs">{r.purpose || "—"}</Text>,
                },
                {
                  key: "actions",
                  header: "Responsibility Coverage",
                  align: "right",
                  render: (r) => (
                    <Group justify="flex-end" gap="xs">
                      <Button
                        size="xs"
                        color="green"
                        leftSection={<FaCheck size={12} />}
                        loading={substituteRespond.isPending}
                        onClick={() => handleSubstituteResponse(r.id, true)}
                      >
                        Accept
                      </Button>
                      <Button
                        size="xs"
                        color="red"
                        variant="light"
                        leftSection={<FaTimes size={12} />}
                        loading={substituteRespond.isPending}
                        onClick={() => handleSubstituteResponse(r.id, false)}
                      >
                        Decline
                      </Button>
                    </Group>
                  ),
                },
              ]}
              empty={{
                icon: FaHandshake,
                title: "No substitute requests",
                description: "You have not been nominated for duty coverage on any pending leaves.",
              }}
            />
          </Card>
        </Tabs.Panel>
      </Tabs>

      {/* Decision Modal */}
      <Modal
        opened={Boolean(decideModalApp)}
        onClose={() => setDecideModalApp(null)}
        title={
          decideModalApp?.approve ? "Sanction Leave Application" : "Reject Leave Application"
        }
      >
        <Stack gap="sm">
          <Text size="sm">
            You are about to {decideModalApp?.approve ? "sanction" : "reject"} Application #
            {decideModalApp?.app.id} for User #{decideModalApp?.app.user_id} (
            {decideModalApp?.app.chargeable_days} days).
          </Text>
          <Textarea
            label="Decision Note / Remarks"
            placeholder="Official remarks (optional for approval)..."
            value={decisionNote}
            onChange={(e) => setDecisionNote(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setDecideModalApp(null)}>
              Cancel
            </Button>
            <Button
              color={decideModalApp?.approve ? "green" : "red"}
              onClick={handleDecideSubmit}
              loading={decide.isPending}
            >
              Confirm {decideModalApp?.approve ? "Sanction" : "Rejection"}
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Recommendation Modal */}
      <Modal
        opened={Boolean(recommendModalApp)}
        onClose={() => setRecommendModalApp(null)}
        title="Unit Head Recommendation"
      >
        <Stack gap="sm">
          <Text size="sm">
            Record recommendation for higher-sanction leave (#{recommendModalApp?.app.id}) before
            forwarding to the Sanctioning Authority.
          </Text>
          <Textarea
            label="Recommendation Remarks"
            placeholder="e.g. Work is covered; leave recommended."
            value={recommendNote}
            onChange={(e) => setRecommendNote(e.currentTarget.value)}
            required
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setRecommendModalApp(null)}>
              Cancel
            </Button>
            <Button
              color={recommendModalApp?.recommended ? "blue" : "orange"}
              onClick={handleRecommendSubmit}
              loading={recommend.isPending}
            >
              Submit {recommendModalApp?.recommended ? "Recommendation" : "Non-recommendation"}
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Cancellation Decision Modal */}
      <Modal
        opened={Boolean(cancelModalApp)}
        onClose={() => setCancelModalApp(null)}
        title="Sanction Cancellation Request"
      >
        <Stack gap="sm">
          <Text size="sm">
            {cancelModalApp?.approve
              ? "Approve cancellation and restore the deducted balance back to the employee."
              : "Decline cancellation and keep the original approved leave active."}
          </Text>
          <Textarea
            label="Authority Remarks"
            value={cancelDecisionNote}
            onChange={(e) => setCancelDecisionNote(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setCancelModalApp(null)}>
              Cancel
            </Button>
            <Button
              color={cancelModalApp?.approve ? "red" : "gray"}
              onClick={handleCancelDecisionSubmit}
              loading={decideCancel.isPending}
            >
              Confirm Decision
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Resumption Review Modal */}
      <Modal
        opened={Boolean(resumptionModalApp)}
        onClose={() => setResumptionModalApp(null)}
        title="Verify Duty Resumption & Sync Balance"
      >
        <Stack gap="sm">
          <Text size="sm">
            Resumption reported on: <strong>{resumptionModalApp?.actual_resumption_date}</strong>.
            Confirming this will recalculate the actual availed days and adjust the employee balance
            automatically (refunding days if early, or debiting if late).
          </Text>
          <Textarea
            label="Verification Note"
            placeholder="e.g. Verified attendance register."
            value={resumptionReviewNote}
            onChange={(e) => setResumptionReviewNote(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setResumptionModalApp(null)}>
              Cancel
            </Button>
            <Button
              color="teal"
              onClick={handleResumptionReviewSubmit}
              loading={reviewResumption.isPending}
            >
              Verify & Reconcile
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
