import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Table,
  Tabs,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCheck, FaTimes, FaUserCheck, FaUserClock } from "react-icons/fa";
import { PageHeader } from "../../../ui/components/PageHeader";
import { ErrorState } from "../../../ui/components/ErrorState";
import { errorMessage } from "../../../lib/http";
import {
  useDecideApproval,
  usePendingApprovals,
  usePendingSubstituteRequests,
  useRespondSubstitute,
} from "../api/hooks";

export default function LeaveTasksPage() {
  const { data: approvals, error: approvalsError } = usePendingApprovals();
  const { data: substitutes, error: subError } = usePendingSubstituteRequests();

  const decide = useDecideApproval();
  const respondSub = useRespondSubstitute();

  const [comments, setComments] = useState<Record<number, string>>({});

  if (approvalsError || subError) {
    return (
      <Container size="xl">
        <ErrorState error={approvalsError || subError} />
      </Container>
    );
  }

  function handleDecision(stepId: number, decision: string) {
    decide.mutate(
      { stepId, decision, comment: comments[stepId] || "" },
      {
        onSuccess: () => {
          notifications.show({
            color: decision === "approved" || decision === "recommended" ? "green" : "red",
            title: "Decision Recorded",
            message: `Recorded ${decision.replace("_", " ")} for step #${stepId}.`,
          });
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Decision Failed",
            message: errorMessage(err),
          });
        },
      }
    );
  }

  function handleSubstitute(applicationId: number, accept: boolean) {
    respondSub.mutate(
      { applicationId, accept },
      {
        onSuccess: () => {
          notifications.show({
            color: accept ? "green" : "orange",
            title: accept ? "Responsibility Accepted" : "Responsibility Declined",
            message: `Substitute consent ${accept ? "granted" : "declined"} for request #${applicationId}.`,
          });
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

  return (
    <Container size="xl">
      <PageHeader
        title="Leave Inbox & Approvals"
        subtitle="Manage pending approval decisions, recommendations, and substitute coverage consent (CW-EL-01)"
      />

      <Tabs defaultValue="approvals">
        <Tabs.List mb="md">
          <Tabs.Tab
            value="approvals"
            leftSection={<FaUserCheck />}
            rightSection={<Badge size="xs" circle>{approvals?.length || 0}</Badge>}
          >
            Pending Approvals
          </Tabs.Tab>
          <Tabs.Tab
            value="substitutes"
            leftSection={<FaUserClock />}
            rightSection={<Badge size="xs" circle color="orange">{substitutes?.length || 0}</Badge>}
          >
            Substitute Requests
          </Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="approvals">
          <Card withBorder radius="md">
            <Title order={4} mb="md">Actionable Approval Tasks</Title>
            {(!approvals || approvals.length === 0) ? (
              <Text c="dimmed">No pending leave approvals assigned to you.</Text>
            ) : (
              <Table striped highlightOnHover>
                <Table.Thead>
                  <Table.Tr>
                              <Table.Th>Application</Table.Th>
                    <Table.Th>Role</Table.Th>
                    <Table.Th>Step Type</Table.Th>
                    <Table.Th>Order</Table.Th>
                    <Table.Th>Comment</Table.Th>
                    <Table.Th>Actions</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {approvals.map((step) => {
                    const isRec = step.step_type === "recommendation";
                    return (
                      <Table.Tr key={step.id}>
                        <Table.Td>
                          <Text fw={700}>#{step.application_id} · {step.application.category}</Text>
                          <Text size="xs" c="dimmed">
                            User #{step.application.user_id} · {step.application.leave_start} to {step.application.leave_end}
                          </Text>
                          <Text size="xs" lineClamp={2}>{step.application.purpose}</Text>
                        </Table.Td>
                        <Table.Td>
                          <Badge variant="outline">{step.assigned_role}</Badge>
                        </Table.Td>
                        <Table.Td>
                          <Badge color={isRec ? "cyan" : "violet"}>
                            {step.step_type.replace("_", " ")}
                          </Badge>
                        </Table.Td>
                        <Table.Td>Step {step.step_order}</Table.Td>
                        <Table.Td style={{ minWidth: 200 }}>
                          <TextInput
                            placeholder="Optional comment"
                            size="xs"
                            value={comments[step.id] || ""}
                            onChange={(e) =>
                              setComments({ ...comments, [step.id]: e.target.value })
                            }
                          />
                        </Table.Td>
                        <Table.Td>
                          <Group gap="xs">
                            {isRec ? (
                              <>
                                <Button
                                  size="xs"
                                  color="teal"
                                  loading={decide.isPending}
                                  onClick={() => handleDecision(step.id, "recommended")}
                                >
                                  Recommend
                                </Button>
                                <Button
                                  size="xs"
                                  color="orange"
                                  variant="light"
                                  loading={decide.isPending}
                                  onClick={() => handleDecision(step.id, "not_recommended")}
                                >
                                  Not Rec.
                                </Button>
                              </>
                            ) : (
                              <>
                                <Button
                                  size="xs"
                                  color="green"
                                  leftSection={<FaCheck />}
                                  loading={decide.isPending}
                                  onClick={() => handleDecision(step.id, "approved")}
                                >
                                  Approve
                                </Button>
                                <Button
                                  size="xs"
                                  color="red"
                                  variant="outline"
                                  leftSection={<FaTimes />}
                                  loading={decide.isPending}
                                  onClick={() => handleDecision(step.id, "rejected")}
                                >
                                  Reject
                                </Button>
                              </>
                            )}
                          </Group>
                        </Table.Td>
                      </Table.Tr>
                    );
                  })}
                </Table.Tbody>
              </Table>
            )}
          </Card>
        </Tabs.Panel>

        <Tabs.Panel value="substitutes">
          <Card withBorder radius="md">
            <Title order={4} mb="md">Substitute Coverage Nominations</Title>
            {(!substitutes || substitutes.length === 0) ? (
              <Text c="dimmed">No substitute requests waiting for your response.</Text>
            ) : (
              <Table striped highlightOnHover>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>App ID</Table.Th>
                    <Table.Th>Applicant</Table.Th>
                    <Table.Th>Category</Table.Th>
                    <Table.Th>Dates</Table.Th>
                    <Table.Th>Duration</Table.Th>
                    <Table.Th>Purpose</Table.Th>
                    <Table.Th>Consent Action</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {substitutes.map((app) => (
                    <Table.Tr key={app.id}>
                      <Table.Td fw={700}>#{app.id}</Table.Td>
                      <Table.Td>User #{app.user_id}</Table.Td>
                      <Table.Td><Badge>{app.category}</Badge></Table.Td>
                      <Table.Td>{app.leave_start} to {app.leave_end}</Table.Td>
                      <Table.Td fw={600}>{app.computed_days}d</Table.Td>
                      <Table.Td style={{ maxWidth: 300 }}>
                        <Text size="sm" lineClamp={2}>{app.purpose}</Text>
                      </Table.Td>
                      <Table.Td>
                        <Group gap="xs">
                          <Button
                            size="xs"
                            color="green"
                            leftSection={<FaCheck />}
                            loading={respondSub.isPending}
                            onClick={() => handleSubstitute(app.id, true)}
                          >
                            Accept
                          </Button>
                          <Button
                            size="xs"
                            color="red"
                            variant="light"
                            leftSection={<FaTimes />}
                            loading={respondSub.isPending}
                            onClick={() => handleSubstitute(app.id, false)}
                          >
                            Decline
                          </Button>
                        </Group>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            )}
          </Card>
        </Tabs.Panel>
      </Tabs>
    </Container>
  );
}
