import React, { useEffect, useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  Stack,
  Table,
  Text,
  Textarea,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { errorMessage, http } from "../../../lib/http";
import type { LeaveApplication } from "../types";

export const LeaveSanctionsPage: React.FC = () => {
  const [sanctions, setSanctions] = useState<LeaveApplication[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedApp, setSelectedApp] = useState<LeaveApplication | null>(null);
  const [actionType, setActionType] = useState<"approve" | "reject">("approve");
  const [remarks, setRemarks] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [opened, setOpened] = useState(false);

  const fetchSanctions = async () => {
    try {
      const res = await http.get<LeaveApplication[]>("/elm/sanctions/pending");
      setSanctions(res.data);
    } catch (err) {
      notifications.show({
        title: "Error",
        message: errorMessage(err),
        color: "red",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchSanctions();
  }, []);

  const handleAction = async () => {
    if (!selectedApp) return;
    setSubmitting(true);
    try {
      await http.post(`/elm/applications/${selectedApp.id}/sanction`, {
        action: actionType,
        remarks: remarks.trim(),
      });
      notifications.show({
        title: "Sanction Decision Recorded",
        message: `Leave #${selectedApp.id} ${actionType}d successfully.`,
        color: actionType === "approve" ? "green" : "red",
      });
      setOpened(false);
      void fetchSanctions();
    } catch (err) {
      notifications.show({
        title: "Sanction Failed",
        message: errorMessage(err),
        color: "red",
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Container size="xl" py="xl">
      <Stack gap="lg">
        <div>
          <Title order={2}>Sanctioning Authority Approvals</Title>
          <Text c="dimmed" size="sm">
            Final approval / rejection portal for higher-sanction leave requests (SCL, EL, COL,
            VL, and Director self-sanction).
          </Text>
        </div>

        <Card withBorder shadow="xs" radius="md">
          {loading ? (
            <Text p="md">Loading sanction requests...</Text>
          ) : sanctions.length === 0 ? (
            <Text p="xl" ta="center" c="dimmed">
              No leave applications awaiting final sanction decision.
            </Text>
          ) : (
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>App #</Table.Th>
                  <Table.Th>Employee</Table.Th>
                  <Table.Th>Category</Table.Th>
                  <Table.Th>Period</Table.Th>
                  <Table.Th>Chargeable Days</Table.Th>
                  <Table.Th>Unit Head Recommendation</Table.Th>
                  <Table.Th>Status</Table.Th>
                  <Table.Th>Action</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {sanctions.map((s) => (
                  <Table.Tr key={s.id}>
                    <Table.Td fw={600}>#{s.id}</Table.Td>
                    <Table.Td>User #{s.user_id}</Table.Td>
                    <Table.Td>
                      <Badge variant="light">{s.leave_category}</Badge>
                    </Table.Td>
                    <Table.Td>
                      {s.start_date} to {s.end_date}
                    </Table.Td>
                    <Table.Td>{s.chargeable_days}</Table.Td>
                    <Table.Td>
                      <Badge
                        color={
                          s.unit_head_recommendation === "recommended" ? "green" : "orange"
                        }
                        size="xs"
                      >
                        {s.unit_head_recommendation || "Self-Sanction"}
                      </Badge>
                    </Table.Td>
                    <Table.Td>
                      <Badge size="xs" color="gray">
                        {s.status_display}
                      </Badge>
                    </Table.Td>
                    <Table.Td>
                      <Group gap="xs">
                        <Button
                          size="xs"
                          color="green"
                          onClick={() => {
                            setSelectedApp(s);
                            setActionType("approve");
                            setRemarks("");
                            setOpened(true);
                          }}
                        >
                          Approve
                        </Button>
                        <Button
                          size="xs"
                          color="red"
                          variant="light"
                          onClick={() => {
                            setSelectedApp(s);
                            setActionType("reject");
                            setRemarks("");
                            setOpened(true);
                          }}
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
      </Stack>

      <Modal opened={opened} onClose={() => setOpened(false)} title="Record Sanction Decision">
        <Stack gap="md">
          <Text size="sm">
            Make final sanctioning decision for Leave Application #{selectedApp?.id} (
            {selectedApp?.leave_category} for {selectedApp?.chargeable_days} days).
          </Text>
          <Text size="xs" c="dimmed">
            Reason: {selectedApp?.reason}
          </Text>
          <Textarea
            label="Sanction Remarks"
            placeholder="Official sanction remarks or conditions"
            value={remarks}
            onChange={(e) => setRemarks(e.target.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setOpened(false)}>
              Cancel
            </Button>
            <Button
              color={actionType === "approve" ? "green" : "red"}
              loading={submitting}
              onClick={handleAction}
            >
              Confirm {actionType.toUpperCase()}
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
};

export default LeaveSanctionsPage;
