import {
  Badge,
  Button,
  Card,
  Center,
  Group,
  Loader,
  Modal,
  Select,
  Stack,
  Table,
  Text,
  Textarea,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useState } from "react";

import { errorMessage } from "../../../lib/http";
import {
  useApprovals,
  useEstablishmentRoute,
  useReviewCancellation,
  useReviewResumption,
  useSanctionDecision,
  useUnitHeadReview,
} from "../api/hooks";
import type { LeaveApplication } from "../api/types";

export function LeaveApprovalsView() {
  const { data: approvals, isPending } = useApprovals();

  const unitHeadMutation = useUnitHeadReview();
  const esttMutation = useEstablishmentRoute();
  const sanctionMutation = useSanctionDecision();
  const cancelReviewMutation = useReviewCancellation();
  const resumeReviewMutation = useReviewResumption();

  const [activeApp, setActiveApp] = useState<LeaveApplication | null>(null);
  const [decision, setDecision] = useState<string>("APPROVED");
  const [remarks, setRemarks] = useState<string>("");

  const handleAction = async () => {
    if (!activeApp) return;

    try {
      if (activeApp.status === "AWAITING_UNIT_HEAD") {
        await unitHeadMutation.mutateAsync({
          id: activeApp.id,
          decision,
          remarks,
        });
      } else if (activeApp.status === "AWAITING_ESTABLISHMENT") {
        await esttMutation.mutateAsync({
          id: activeApp.id,
          remarks,
        });
      } else if (activeApp.status === "AWAITING_SANCTION") {
        await sanctionMutation.mutateAsync({
          id: activeApp.id,
          decision,
          remarks,
        });
      } else if (activeApp.status === "AWAITING_CANCELLATION") {
        await cancelReviewMutation.mutateAsync({
          id: activeApp.id,
          decision,
          remarks,
        });
      } else if (activeApp.resumption_status === "SUBMITTED") {
        await resumeReviewMutation.mutateAsync({
          id: activeApp.id,
          remarks,
        });
      }

      notifications.show({ title: "Review Recorded", message: `Application #${activeApp.id} updated.`, color: "green" });
      setActiveApp(null);
      setRemarks("");
    } catch (e) {
      notifications.show({ title: "Action Failed", message: errorMessage(e), color: "red" });
    }
  };

  return (
    <Stack gap="md">
      <Card withBorder padding="md" radius="md">
        <Title order={4} mb="md">Leave Applications Awaiting Your Action</Title>
        {isPending ? (
          <Center py="xl"><Loader size="md" /></Center>
        ) : !approvals || approvals.length === 0 ? (
          <Center py="xl"><Text c="dimmed">No applications currently pending your review.</Text></Center>
        ) : (
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>ID</Table.Th>
                <Table.Th>Applicant</Table.Th>
                <Table.Th>Type</Table.Th>
                <Table.Th>Period</Table.Th>
                <Table.Th>Days</Table.Th>
                <Table.Th>Current Queue</Table.Th>
                <Table.Th>Action</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {approvals.map((app) => (
                <Table.Tr key={app.id}>
                  <Table.Td>#{app.id}</Table.Td>
                  <Table.Td>User #{app.applicant_user_id}</Table.Td>
                  <Table.Td><Badge>{app.leave_type}</Badge></Table.Td>
                  <Table.Td>{app.start_date} → {app.end_date}</Table.Td>
                  <Table.Td>{app.days_count}</Table.Td>
                  <Table.Td>
                    <Badge color="blue">
                      {app.resumption_status === "SUBMITTED" ? "RESUMPTION REVIEW" : app.status}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Button
                      size="xs"
                      onClick={() => {
                        setActiveApp(app);
                        setRemarks("");
                        setDecision(
                          app.leave_type in ["CL", "RH"]
                            ? "APPROVED"
                            : app.status === "AWAITING_UNIT_HEAD"
                            ? "RECOMMENDED"
                            : "APPROVED"
                        );
                      }}
                    >
                      Review
                    </Button>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        )}
      </Card>

      <Modal opened={!!activeApp} onClose={() => setActiveApp(null)} title={`Review Application #${activeApp?.id}`} centered>
        <Stack gap="md">
          <Text size="sm">
            Applicant #{activeApp?.applicant_user_id} ({activeApp?.leave_type}) from {activeApp?.start_date} to {activeApp?.end_date}
          </Text>

          {activeApp?.status === "AWAITING_UNIT_HEAD" && !["CL", "RH"].includes(activeApp.leave_type) ? (
            <Select
              label="Recommendation"
              value={decision}
              onChange={(v) => setDecision(v || "RECOMMENDED")}
              data={[
                { value: "RECOMMENDED", label: "Recommended (Proceed to Sanction)" },
                { value: "NOT_RECOMMENDED", label: "Not Recommended" },
              ]}
            />
          ) : activeApp?.status !== "AWAITING_ESTABLISHMENT" && activeApp?.resumption_status !== "SUBMITTED" ? (
            <Select
              label="Decision"
              value={decision}
              onChange={(v) => setDecision(v || "APPROVED")}
              data={[
                { value: "APPROVED", label: "Approve" },
                { value: "REJECTED", label: "Reject" },
              ]}
            />
          ) : null}

          <Textarea
            label="Remarks / Comments"
            required={activeApp?.status === "AWAITING_ESTABLISHMENT"}
            placeholder="Enter reason or comments"
            value={remarks}
            onChange={(e) => setRemarks(e.target.value)}
          />

          <Group justify="flex-end">
            <Button variant="default" onClick={() => setActiveApp(null)}>Cancel</Button>
            <Button onClick={handleAction}>Submit Decision</Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}
