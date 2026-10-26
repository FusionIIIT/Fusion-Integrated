import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Table,
  Text,
  TextInput,
} from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useDecideCancellation,
  useDecideLeaveApproval,
  useLeaveApprovalQueue,
  useRespondSubstitute,
  useReviewDutyResumption,
} from "../api/hooks";

export default function LeaveApprovalsPage() {
  const queue = useLeaveApprovalQueue();
  const decide = useDecideLeaveApproval();
  const decideCancel = useDecideCancellation();
  const respondSub = useRespondSubstitute();
  const reviewResumption = useReviewDutyResumption();

  const [remarks, setRemarks] = useState<Record<number, string>>({});

  if (queue.error) {
    return (
      <Container size="lg">
        <ErrorState error={queue.error} />
      </Container>
    );
  }

  const items = queue.data?.results ?? [];

  return (
    <Container size="lg">
      <PageHeader
        title="Leave Approvals"
        subtitle="Review, recommend, sanction, and manage pending leave applications"
      />
      <Card withBorder padding="lg">
        {items.length === 0 ? (
          <Text size="sm" c="dimmed">
            No pending leave applications in the approval queue.
          </Text>
        ) : (
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Applicant ID</Table.Th>
                <Table.Th>Leave Type</Table.Th>
                <Table.Th>Dates</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Remarks</Table.Th>
                <Table.Th>Actions</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {items.map((item) => (
                <Table.Tr key={item.id}>
                  <Table.Td>{item.user_id}</Table.Td>
                  <Table.Td>
                    {item.leave_type.name}
                    {item.is_extension && <Badge size="xs" ml="xs">Extension</Badge>}
                  </Table.Td>
                  <Table.Td>
                    {item.start_date} to {item.end_date}
                  </Table.Td>
                  <Table.Td>
                    <Badge variant="light">{item.status}</Badge>
                    {item.resumption_status === "pending_review" && (
                      <Badge color="teal" size="xs" ml="xs">
                        Resumption Pending
                      </Badge>
                    )}
                  </Table.Td>
                  <Table.Td>
                    <TextInput
                      size="xs"
                      placeholder="Add remark"
                      value={remarks[item.id] ?? ""}
                      onChange={(e) => {
                        const val = e.currentTarget.value;
                        setRemarks((prev) => ({
                          ...prev,
                          [item.id]: val,
                        }));
                      }}
                    />
                  </Table.Td>
                  <Table.Td>
                    <Group gap="xs">
                      {/* Substitute decision */}
                      {item.status === "awaiting_substitute" && (
                        <>
                          <Button
                            size="xs"
                            color="green"
                            loading={respondSub.isPending}
                            onClick={() =>
                              respondSub.mutate({ id: item.id, decision: "accepted" })
                            }
                          >
                            Accept
                          </Button>
                          <Button
                            size="xs"
                            color="red"
                            variant="light"
                            loading={respondSub.isPending}
                            onClick={() =>
                              respondSub.mutate({ id: item.id, decision: "declined" })
                            }
                          >
                            Decline
                          </Button>
                        </>
                      )}

                      {/* Staged Cancellation: Unit Head recommendation */}
                      {item.status === "cancellation_pending_unit_head" && (
                        <>
                          <Button
                            size="xs"
                            color="blue"
                            variant="light"
                            loading={decideCancel.isPending}
                            onClick={() =>
                              decideCancel.mutate({
                                id: item.id,
                                decision: "recommended",
                                remarks: remarks[item.id],
                              })
                            }
                          >
                            Recommend Cancel
                          </Button>
                          <Button
                            size="xs"
                            color="red"
                            variant="light"
                            loading={decideCancel.isPending}
                            onClick={() =>
                              decideCancel.mutate({
                                id: item.id,
                                decision: "rejected",
                                remarks: remarks[item.id],
                              })
                            }
                          >
                            Reject Cancel
                          </Button>
                        </>
                      )}

                      {/* Staged Cancellation: Final Sanction */}
                      {item.status === "cancellation_pending_final" && (
                        <>
                          <Button
                            size="xs"
                            color="green"
                            loading={decideCancel.isPending}
                            onClick={() =>
                              decideCancel.mutate({
                                id: item.id,
                                decision: "approved",
                                remarks: remarks[item.id],
                              })
                            }
                          >
                            Approve Cancel
                          </Button>
                          <Button
                            size="xs"
                            color="red"
                            variant="light"
                            loading={decideCancel.isPending}
                            onClick={() =>
                              decideCancel.mutate({
                                id: item.id,
                                decision: "rejected",
                                remarks: remarks[item.id],
                              })
                            }
                          >
                            Reject Cancel
                          </Button>
                        </>
                      )}

                      {/* Duty Resumption review */}
                      {item.resumption_status === "pending_review" && (
                        <Button
                          size="xs"
                          color="teal"
                          loading={reviewResumption.isPending}
                          onClick={() =>
                            reviewResumption.mutate({
                              id: item.id,
                              remarks: remarks[item.id],
                            })
                          }
                        >
                          Review Resumption
                        </Button>
                      )}

                      {/* Standard Leave Decisions: Recommend / Approve / Reject */}
                      {[
                        "pending",
                        "awaiting_unit_head",
                        "awaiting_final_sanction",
                        "recommended",
                        "awaiting_director",
                      ].includes(item.status) && (
                        <>
                          <Button
                            size="xs"
                            color="blue"
                            variant="light"
                            loading={decide.isPending}
                            onClick={() =>
                              decide.mutate({
                                id: item.id,
                                decision: "recommended",
                                remarks: remarks[item.id],
                              })
                            }
                          >
                            Recommend
                          </Button>
                          <Button
                            size="xs"
                            color="green"
                            loading={decide.isPending}
                            onClick={() =>
                              decide.mutate({
                                id: item.id,
                                decision: "approved",
                                remarks: remarks[item.id],
                              })
                            }
                          >
                            Approve
                          </Button>
                          <Button
                            size="xs"
                            color="red"
                            variant="light"
                            loading={decide.isPending}
                            onClick={() =>
                              decide.mutate({
                                id: item.id,
                                decision: "rejected",
                                remarks: remarks[item.id],
                              })
                            }
                          >
                            Reject
                          </Button>
                        </>
                      )}
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        )}
      </Card>
    </Container>
  );
}
