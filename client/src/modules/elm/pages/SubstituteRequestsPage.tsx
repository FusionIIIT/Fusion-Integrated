import { useState } from "react";
import {
  Badge, Button, Card, Container, Group, Modal, Stack, Table, Text, Textarea
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { PageHeader } from "../../../ui/components/PageHeader";
import { useSubstituteResponses, useRespondSubstitute } from "../api/hooks";
import type { SubstituteResponse } from "../api/types";

export default function SubstituteRequestsPage() {
  const { data: requests, isPending } = useSubstituteResponses();
  const respondMutation = useRespondSubstitute();

  const [selectedReq, setSelectedReq] = useState<SubstituteResponse | null>(null);
  const [responseAction, setResponseAction] = useState<"ACCEPTED" | "DECLINED" | null>(null);
  const [remarks, setRemarks] = useState("");

  const handleOpenAction = (req: SubstituteResponse, action: "ACCEPTED" | "DECLINED") => {
    setSelectedReq(req);
    setResponseAction(action);
    setRemarks("");
  };

  const handleSubmitResponse = async () => {
    if (!selectedReq || !responseAction) return;

    try {
      await respondMutation.mutateAsync({
        id: selectedReq.id,
        status: responseAction,
        remarks,
      });
      notifications.show({
        title: responseAction === "ACCEPTED" ? "Responsibility Accepted" : "Responsibility Declined",
        message: `Response submitted for Leave Request #${selectedReq.leave_request_id}`,
        color: responseAction === "ACCEPTED" ? "teal" : "orange",
      });
      setSelectedReq(null);
      setResponseAction(null);
    } catch (err: any) {
      notifications.show({
        title: "Action failed",
        message: err.message || "Failed to submit substitute response",
        color: "red",
      });
    }
  };

  return (
    <Container size="lg">
      <PageHeader
        title="Substitute Responses"
        subtitle="Review and respond to colleague requests nominated for academic/administrative responsibility coverage (CW-EL-01, BR-EL-014, BR-EL-015)"
      />

      <Card padding="md" shadow="xs" radius="md">
        {isPending ? (
          <Text c="dimmed">Loading substitute requests...</Text>
        ) : !requests || requests.length === 0 ? (
          <Text c="dimmed">No pending substitute coverage requests.</Text>
        ) : (
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Request #</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Remarks</Table.Th>
                <Table.Th>Responded At</Table.Th>
                <Table.Th>Action</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {requests.map((r) => (
                <Table.Tr key={r.id}>
                  <Table.Td>#{r.leave_request_id}</Table.Td>
                  <Table.Td>
                    <Badge color={r.status === "ACCEPTED" ? "teal" : r.status === "DECLINED" ? "red" : "blue"}>
                      {r.status}
                    </Badge>
                  </Table.Td>
                  <Table.Td>{r.remarks || "-"}</Table.Td>
                  <Table.Td>{r.responded_at ? new Date(r.responded_at).toLocaleDateString() : "-"}</Table.Td>
                  <Table.Td>
                    {r.status === "PENDING" && (
                      <Group gap="xs">
                        <Button
                          size="xs"
                          color="teal"
                          onClick={() => handleOpenAction(r, "ACCEPTED")}
                        >
                          Accept
                        </Button>
                        <Button
                          size="xs"
                          color="red"
                          variant="light"
                          onClick={() => handleOpenAction(r, "DECLINED")}
                        >
                          Decline
                        </Button>
                      </Group>
                    )}
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        )}
      </Card>

      <Modal
        opened={!!selectedReq}
        onClose={() => setSelectedReq(null)}
        title={responseAction === "ACCEPTED" ? "Accept Substitute Responsibility" : "Decline Substitute Responsibility"}
      >
        <Stack>
          <Text size="sm">
            {responseAction === "ACCEPTED"
              ? `Confirm that you accept responsibility coverage for Leave Request #${selectedReq?.leave_request_id}. Once confirmed, the application will proceed to Unit Head review.`
              : `Declining coverage will notify the applicant to nominate an alternate substitute or withdraw their request (BR-EL-015).`}
          </Text>
          <Textarea
            label="Remarks (optional)"
            placeholder="Add coverage arrangement notes or reason for decline"
            value={remarks}
            onChange={(e) => setRemarks(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setSelectedReq(null)}>Cancel</Button>
            <Button
              color={responseAction === "ACCEPTED" ? "teal" : "red"}
              loading={respondMutation.isPending}
              onClick={handleSubmitResponse}
            >
              Confirm {responseAction === "ACCEPTED" ? "Acceptance" : "Decline"}
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
