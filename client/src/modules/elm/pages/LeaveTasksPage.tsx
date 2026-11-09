import {
  Badge,
  Button,
  Group,
  Loader,
  Paper,
  Stack,
  Table,
  Tabs,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { useState } from "react";
import {
  useRespondSubstitute,
  useReviewDecision,
  useReviewTasks,
  useSubstituteTasks,
} from "../api/hooks";

export default function LeaveTasksPage() {
  const subTasks = useSubstituteTasks();
  const revTasks = useReviewTasks();
  const respondMutation = useRespondSubstitute();
  const reviewMutation = useReviewDecision();

  const [remarks, setRemarks] = useState<Record<number, string>>({});
  const [reasons, setReasons] = useState<Record<number, string>>({});

  return (
    <Stack gap="lg">
      <Title order={2}>Leave Tasks & Approvals</Title>

      <Tabs defaultValue="substitute">
        <Tabs.List>
          <Tabs.Tab value="substitute">
            Substitute Requests ({subTasks.data?.length || 0})
          </Tabs.Tab>
          <Tabs.Tab value="review">
            Pending Approvals ({revTasks.data?.length || 0})
          </Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="substitute" pt="md">
          {subTasks.isLoading ? (
            <Loader />
          ) : subTasks.data?.length === 0 ? (
            <Text c="dimmed">No pending substitute requests.</Text>
          ) : (
            <Paper shadow="xs" p="md" withBorder>
              <Table>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Applicant ID</Table.Th>
                    <Table.Th>Category</Table.Th>
                    <Table.Th>Dates</Table.Th>
                    <Table.Th>Purpose</Table.Th>
                    <Table.Th>Remarks</Table.Th>
                    <Table.Th>Actions</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {subTasks.data?.map((req) => (
                    <Table.Tr key={req.id}>
                      <Table.Td>{req.user_id}</Table.Td>
                      <Table.Td>{req.category}</Table.Td>
                      <Table.Td>{req.start_date} to {req.end_date}</Table.Td>
                      <Table.Td>{req.purpose}</Table.Td>
                      <Table.Td>
                        <TextInput
                          placeholder="Optional remarks"
                          value={remarks[req.id] || ""}
                          onChange={(e) =>
                            setRemarks({ ...remarks, [req.id]: e.target.value })
                          }
                        />
                      </Table.Td>
                      <Table.Td>
                        <Group gap="xs">
                          <Button
                            size="xs"
                            color="green"
                            onClick={() =>
                              respondMutation.mutate({
                                requestId: req.id,
                                action: "accept",
                                remarks: remarks[req.id],
                              })
                            }
                          >
                            Accept
                          </Button>
                          <Button
                            size="xs"
                            color="red"
                            variant="light"
                            onClick={() =>
                              respondMutation.mutate({
                                requestId: req.id,
                                action: "decline",
                                remarks: remarks[req.id],
                              })
                            }
                          >
                            Decline
                          </Button>
                        </Group>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Paper>
          )}
        </Tabs.Panel>

        <Tabs.Panel value="review" pt="md">
          {revTasks.isLoading ? (
            <Loader />
          ) : revTasks.data?.length === 0 ? (
            <Text c="dimmed">No pending review tasks.</Text>
          ) : (
            <Paper shadow="xs" p="md" withBorder>
              <Table>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Applicant ID</Table.Th>
                    <Table.Th>Category</Table.Th>
                    <Table.Th>Dates</Table.Th>
                    <Table.Th>Days</Table.Th>
                    <Table.Th>Status</Table.Th>
                    <Table.Th>Comments / Reason</Table.Th>
                    <Table.Th>Actions</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {revTasks.data?.map((req) => (
                    <Table.Tr key={req.id}>
                      <Table.Td>{req.user_id}</Table.Td>
                      <Table.Td>{req.category}</Table.Td>
                      <Table.Td>{req.start_date} to {req.end_date}</Table.Td>
                      <Table.Td>{req.leave_days}</Table.Td>
                      <Table.Td>
                        <Badge>{req.status}</Badge>
                      </Table.Td>
                      <Table.Td>
                        <TextInput
                          placeholder="Review comments"
                          value={reasons[req.id] || ""}
                          onChange={(e) =>
                            setReasons({ ...reasons, [req.id]: e.target.value })
                          }
                        />
                      </Table.Td>
                      <Table.Td>
                        <Group gap="xs">
                          {["CL", "RH"].includes(req.category) ? (
                            <Button
                              size="xs"
                              color="green"
                              onClick={() =>
                                reviewMutation.mutate({
                                  requestId: req.id,
                                  action: "approve",
                                  reason: reasons[req.id],
                                })
                              }
                            >
                              Approve
                            </Button>
                          ) : (
                            <Button
                              size="xs"
                              color="blue"
                              onClick={() =>
                                reviewMutation.mutate({
                                  requestId: req.id,
                                  action: "recommend",
                                  reason: reasons[req.id],
                                })
                              }
                            >
                              Recommend
                            </Button>
                          )}
                          <Button
                            size="xs"
                            color="red"
                            variant="light"
                            onClick={() =>
                              reviewMutation.mutate({
                                requestId: req.id,
                                action: "reject",
                                reason: reasons[req.id],
                              })
                            }
                          >
                            Reject
                          </Button>
                        </Group>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Paper>
          )}
        </Tabs.Panel>
      </Tabs>
    </Stack>
  );
}
