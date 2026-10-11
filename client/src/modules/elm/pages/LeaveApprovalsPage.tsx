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
import { useDecideLeaveApproval, useLeaveApprovalQueue } from "../api/hooks";

export default function LeaveApprovalsPage() {
  const queue = useLeaveApprovalQueue();
  const decide = useDecideLeaveApproval();
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
        subtitle="Review and sanction pending employee leave applications"
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
                  <Table.Td>{item.leave_type.name}</Table.Td>
                  <Table.Td>
                    {item.start_date} to {item.end_date}
                  </Table.Td>
                  <Table.Td>
                    <Badge variant="light">{item.status}</Badge>
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
