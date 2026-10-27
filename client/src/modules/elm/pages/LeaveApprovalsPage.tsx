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
import type { LeaveRequest, LeaveExtension, LeaveResumption } from "../types";

export default function LeaveApprovalsPage() {
  const [stage, setStage] = useState<"unit_head" | "sanction" | "extensions" | "resumptions">("unit_head");
  const [queue, setQueue] = useState<LeaveRequest[]>([]);
  const [extensionsQueue, setExtensionsQueue] = useState<LeaveExtension[]>([]);
  const [resumptionsQueue, setResumptionsQueue] = useState<LeaveResumption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Decision Modal
  const [activeRequest, setActiveRequest] = useState<LeaveRequest | null>(null);
  const [activeExt, setActiveExt] = useState<LeaveExtension | null>(null);
  const [activeRes, setActiveRes] = useState<LeaveResumption | null>(null);
  const [actionType, setActionType] = useState<"approve" | "reject" | "recommend" | "not_recommend">("approve");
  const [remarks, setRemarks] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const fetchQueue = async () => {
    setLoading(true);
    setError(null);
    try {
      if (stage === "unit_head" || stage === "sanction") {
        const data = await elmApi.getApprovalQueue(stage);
        setQueue(data);
      } else if (stage === "extensions") {
        const data = await elmApi.getExtensionQueue();
        setExtensionsQueue(data);
      } else if (stage === "resumptions") {
        const data = await elmApi.getResumptionQueue();
        setResumptionsQueue(data);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load approval queue.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueue();
  }, [stage]);

  const handleDecision = async () => {
    setSubmitting(true);
    try {
      if (activeRequest && (stage === "unit_head" || stage === "sanction")) {
        await elmApi.actApproval(activeRequest.id, stage, actionType, remarks);
        notifications.show({
          title: "Action Recorded",
          message: `Decision '${actionType}' recorded for Leave #${activeRequest.id}.`,
          color: "green",
        });
      } else if (activeExt) {
        await elmApi.reviewExtension(activeExt.id, actionType as "approve" | "reject", remarks);
        notifications.show({
          title: "Extension Decision",
          message: `Extension #${activeExt.id} ${actionType}ed.`,
          color: "green",
        });
      } else if (activeRes) {
        await elmApi.reviewResumption(activeRes.id, remarks);
        notifications.show({
          title: "Resumption Approved",
          message: `Resumption #${activeRes.id} reviewed and balance synchronized.`,
          color: "green",
        });
      }
      setActiveRequest(null);
      setActiveExt(null);
      setActiveRes(null);
      setRemarks("");
      fetchQueue();
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
        title="Leave Approvals & Reviews"
        subtitle="Review, recommend, and sanction employee leave requests, extensions, and duty resumptions."
      />

      {error && (
        <Alert color="red" mb="md" title="Notice">
          {error}
        </Alert>
      )}

      <Group justify="space-between" mb="md">
        <SegmentedControl
          value={stage}
          onChange={(val) => setStage(val as typeof stage)}
          data={[
            { label: "Unit Head Queue", value: "unit_head" },
            { label: "Higher Sanction", value: "sanction" },
            { label: "Leave Extensions", value: "extensions" },
            { label: "Duty Resumptions", value: "resumptions" },
          ]}
        />
      </Group>

      {loading ? (
        <Group justify="center" py="xl">
          <Loader />
        </Group>
      ) : stage === "extensions" ? (
        <Card withBorder radius="md">
          <Table verticalSpacing="sm" highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Ext ID</Table.Th>
                <Table.Th>Leave ID</Table.Th>
                <Table.Th>Additional Period</Table.Th>
                <Table.Th>Duration</Table.Th>
                <Table.Th>Reason</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Actions</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {extensionsQueue.length === 0 ? (
                <Table.Tr>
                  <Table.Td colSpan={7}>
                    <Text c="dimmed" ta="center" py="md">
                      No pending leave extension requests.
                    </Text>
                  </Table.Td>
                </Table.Tr>
              ) : (
                extensionsQueue.map((ext) => (
                  <Table.Tr key={ext.id}>
                    <Table.Td>#{ext.id}</Table.Td>
                    <Table.Td>#{ext.leave_request_id}</Table.Td>
                    <Table.Td>{ext.start_date} to {ext.end_date}</Table.Td>
                    <Table.Td fw={600}>+{ext.duration_days} days</Table.Td>
                    <Table.Td style={{ maxWidth: 250 }}><Text size="sm" lineClamp={2}>{ext.reason}</Text></Table.Td>
                    <Table.Td><Badge color="blue">{ext.status}</Badge></Table.Td>
                    <Table.Td>
                      <Group gap="xs">
                        <Button
                          size="xs"
                          color="green"
                          onClick={() => {
                            setActiveExt(ext);
                            setActionType("approve");
                          }}
                        >
                          Approve
                        </Button>
                        <Button
                          size="xs"
                          color="red"
                          variant="light"
                          onClick={() => {
                            setActiveExt(ext);
                            setActionType("reject");
                          }}
                        >
                          Reject
                        </Button>
                      </Group>
                    </Table.Td>
                  </Table.Tr>
                ))
              )}
            </Table.Tbody>
          </Table>
        </Card>
      ) : stage === "resumptions" ? (
        <Card withBorder radius="md">
          <Table verticalSpacing="sm" highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Res ID</Table.Th>
                <Table.Th>Leave ID</Table.Th>
                <Table.Th>Expected End</Table.Th>
                <Table.Th>Actual Resumption</Table.Th>
                <Table.Th>Type</Table.Th>
                <Table.Th>Adjusted Days</Table.Th>
                <Table.Th>Actions</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {resumptionsQueue.length === 0 ? (
                <Table.Tr>
                  <Table.Td colSpan={7}>
                    <Text c="dimmed" ta="center" py="md">
                      No pending duty resumption declarations.
                    </Text>
                  </Table.Td>
                </Table.Tr>
              ) : (
                resumptionsQueue.map((res) => (
                  <Table.Tr key={res.id}>
                    <Table.Td>#{res.id}</Table.Td>
                    <Table.Td>#{res.leave_request_id}</Table.Td>
                    <Table.Td>{res.expected_date}</Table.Td>
                    <Table.Td fw={600}>{res.actual_resumption_date}</Table.Td>
                    <Table.Td>
                      <Badge color={res.resumption_type === "normal" ? "teal" : res.resumption_type === "early" ? "blue" : "orange"}>
                        {res.resumption_type.toUpperCase()}
                      </Badge>
                    </Table.Td>
                    <Table.Td>{res.adjusted_duration_days} days</Table.Td>
                    <Table.Td>
                      <Button
                        size="xs"
                        color="teal"
                        onClick={() => {
                          setActiveRes(res);
                          setActionType("approve");
                        }}
                      >
                        Review & Synchronize
                      </Button>
                    </Table.Td>
                  </Table.Tr>
                ))
              )}
            </Table.Tbody>
          </Table>
        </Card>
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
        opened={Boolean(activeRequest || activeExt || activeRes)}
        onClose={() => {
          setActiveRequest(null);
          setActiveExt(null);
          setActiveRes(null);
        }}
        title={`Record Decision: ${actionType.toUpperCase().replace("_", " ")}`}
      >
        <Stack gap="sm">
          <Text size="sm">
            Please confirm your decision and provide any formal remarks or sanction notes.
          </Text>
          <Textarea
            label="Decision Remarks / Comments"
            placeholder="Official remarks or sanction comments"
            value={remarks}
            onChange={(e) => setRemarks(e.currentTarget.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button
              variant="default"
              onClick={() => {
                setActiveRequest(null);
                setActiveExt(null);
                setActiveRes(null);
              }}
            >
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
