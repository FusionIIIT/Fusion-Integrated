import { useEffect, useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  SegmentedControl,
  Stack,
  Table,
  Text,
  Textarea,
  Loader,
  Alert,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCheck, FaTimes, FaThumbsUp, FaThumbsDown } from "react-icons/fa";

import { PageHeader } from "../../../ui/components/PageHeader";
import { elmApi } from "../api/elmApi";
import type { LeaveRequest } from "../types";

export default function LeaveApprovalsPage() {
  const [stage, setStage] = useState<"unit_head" | "sanction">("unit_head");
  const [queue, setQueue] = useState<LeaveRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Decision Modal
  const [activeRequest, setActiveRequest] = useState<LeaveRequest | null>(null);
  const [actionType, setActionType] = useState<
    "approve" | "reject" | "recommend" | "not_recommend"
  >("approve");
  const [remarks, setRemarks] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const fetchQueue = async (currentStage: "unit_head" | "sanction") => {
    setLoading(true);
    setError(null);
    try {
      const data = await elmApi.getApprovalQueue(currentStage);
      setQueue(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load approval queue.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueue(stage);
  }, [stage]);

  const handleDecision = async () => {
    if (!activeRequest) return;
    setSubmitting(true);
    try {
      await elmApi.actApproval(activeRequest.id, stage, actionType, remarks);
      notifications.show({
        title: "Action Recorded",
        message: `Decision '${actionType}' recorded for Leave #${activeRequest.id}.`,
        color: "green",
      });
      setActiveRequest(null);
      setRemarks("");
      fetchQueue(stage);
    } catch (err: unknown) {
      notifications.show({
        title: "Error",
        message: err instanceof Error ? err.message : "Failed to record approval decision.",
        color: "red",
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Container size="xl" py="lg">
      <PageHeader
        title="Leave Approvals & Recommendations"
        subtitle="Review, recommend, and sanction employee leave requests according to institutional hierarchy."
      />

      {error && (
        <Alert color="red" mb="md" title="Notice">
          {error}
        </Alert>
      )}

      <Group justify="space-between" mb="md">
        <SegmentedControl
          value={stage}
          onChange={(val) => setStage(val as "unit_head" | "sanction")}
          data={[
            { label: "Unit Head Queue (Pending Review)", value: "unit_head" },
            { label: "Higher Sanction Queue (Dean / Director)", value: "sanction" },
          ]}
        />
      </Group>

      {loading ? (
        <Group justify="center" py="xl">
          <Loader />
        </Group>
      ) : (
        <Card withBorder radius="md">
          <Table verticalSpacing="sm" highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>ID</Table.Th>
                <Table.Th>Applicant</Table.Th>
                <Table.Th>Category</Table.Th>
                <Table.Th>Period</Table.Th>
                <Table.Th>Days</Table.Th>
                <Table.Th>Station Leave</Table.Th>
                <Table.Th>Substitute Status</Table.Th>
                <Table.Th>Recommendation</Table.Th>
                <Table.Th>Actions</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {queue.length === 0 ? (
                <Table.Tr>
                  <Table.Td colSpan={9}>
                    <Text c="dimmed" ta="center" py="md">
                      No pending requests in this approval queue.
                    </Text>
                  </Table.Td>
                </Table.Tr>
              ) : (
                queue.map((r) => {
                  const isUnitHeadFinal = ["CL", "RH"].includes(r.category);

                  return (
                    <Table.Tr key={r.id}>
                      <Table.Td>#{r.id}</Table.Td>
                      <Table.Td>
                        <Badge variant="light">User #{r.user_id}</Badge>
                      </Table.Td>
                      <Table.Td>
                        <Badge variant="outline">{r.category}</Badge>
                      </Table.Td>
                      <Table.Td>
                        {r.start_date} to {r.end_date}
                      </Table.Td>
                      <Table.Td>{r.duration_days}d</Table.Td>
                      <Table.Td>
                        {r.is_station_leave ? (
                          <Badge size="xs" color="cyan">
                            Station Leave
                          </Badge>
                        ) : (
                          <Text size="xs" c="dimmed">
                            No
                          </Text>
                        )}
                      </Table.Td>
                      <Table.Td>
                        <Badge
                          size="xs"
                          color={r.substitute_status === "accepted" ? "green" : "gray"}
                        >
                          {r.substitute_status}
                        </Badge>
                      </Table.Td>
                      <Table.Td>
                        {r.unit_head_recommendation !== "none" ? (
                          <Badge
                            size="xs"
                            color={
                              r.unit_head_recommendation === "recommended"
                                ? "teal"
                                : "red"
                            }
                          >
                            {r.unit_head_recommendation}
                          </Badge>
                        ) : (
                          <Text size="xs" c="dimmed">
                            —
                          </Text>
                        )}
                      </Table.Td>
                      <Table.Td>
                        <Group gap="xs">
                          {stage === "unit_head" ? (
                            isUnitHeadFinal ? (
                              <>
                                <Button
                                  size="xs"
                                  color="green"
                                  leftSection={<FaCheck size={10} />}
                                  onClick={() => {
                                    setActiveRequest(r);
                                    setActionType("approve");
                                  }}
                                >
                                  Approve
                                </Button>
                                <Button
                                  size="xs"
                                  color="red"
                                  variant="light"
                                  leftSection={<FaTimes size={10} />}
                                  onClick={() => {
                                    setActiveRequest(r);
                                    setActionType("reject");
                                  }}
                                >
                                  Reject
                                </Button>
                              </>
                            ) : (
                              <>
                                <Button
                                  size="xs"
                                  color="teal"
                                  leftSection={<FaThumbsUp size={10} />}
                                  onClick={() => {
                                    setActiveRequest(r);
                                    setActionType("recommend");
                                  }}
                                >
                                  Recommend
                                </Button>
                                <Button
                                  size="xs"
                                  color="orange"
                                  variant="light"
                                  leftSection={<FaThumbsDown size={10} />}
                                  onClick={() => {
                                    setActiveRequest(r);
                                    setActionType("not_recommend");
                                  }}
                                >
                                  Not Recommend
                                </Button>
                              </>
                            )
                          ) : (
                            <>
                              <Button
                                size="xs"
                                color="green"
                                leftSection={<FaCheck size={10} />}
                                onClick={() => {
                                  setActiveRequest(r);
                                  setActionType("approve");
                                }}
                              >
                                Sanction
                              </Button>
                              <Button
                                size="xs"
                                color="red"
                                variant="light"
                                leftSection={<FaTimes size={10} />}
                                onClick={() => {
                                  setActiveRequest(r);
                                  setActionType("reject");
                                }}
                              >
                                Reject
                              </Button>
                            </>
                          )}
                        </Group>
                      </Table.Td>
                    </Table.Tr>
                  );
                })
              )}
            </Table.Tbody>
          </Table>
        </Card>
      )}

      {/* Decision Remarks Modal */}
      <Modal
        opened={Boolean(activeRequest)}
        onClose={() => setActiveRequest(null)}
        title={`Record Decision: ${actionType.toUpperCase().replace("_", " ")}`}
      >
        <Stack gap="sm">
          <Text size="sm">
            You are recording decision <strong>{actionType}</strong> for Leave Application #
            {activeRequest?.id} ({activeRequest?.category}, {activeRequest?.start_date} to{" "}
            {activeRequest?.end_date}).
          </Text>
          <Textarea
            label="Decision Remarks / Comments"
            placeholder="Official remarks or reasons"
            value={remarks}
            onChange={(e) => setRemarks(e.currentTarget.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setActiveRequest(null)}>
              Cancel
            </Button>
            <Button color="blue" loading={submitting} onClick={handleDecision}>
              Confirm Decision
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
