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

export const UnitHeadReviewsPage: React.FC = () => {
  const [reviews, setReviews] = useState<LeaveApplication[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedApp, setSelectedApp] = useState<LeaveApplication | null>(null);
  const [actionType, setActionType] = useState<
    "approve" | "reject" | "recommend" | "not_recommend"
  >("approve");
  const [remarks, setRemarks] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [opened, setOpened] = useState(false);

  const fetchReviews = async () => {
    try {
      const res = await http.get<LeaveApplication[]>("/elm/unit-head/pending");
      setReviews(res.data);
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
    void fetchReviews();
  }, []);

  const handleAction = async () => {
    if (!selectedApp) return;
    setSubmitting(true);
    try {
      await http.post(`/elm/applications/${selectedApp.id}/unit-head-review`, {
        action: actionType,
        remarks: remarks.trim(),
      });
      notifications.show({
        title: "Review Submitted",
        message: `Application #${selectedApp.id} processed as ${actionType}.`,
        color: "green",
      });
      setOpened(false);
      void fetchReviews();
    } catch (err) {
      notifications.show({
        title: "Action Failed",
        message: errorMessage(err),
        color: "red",
      });
    } finally {
      setSubmitting(false);
    }
  };

  const isFinalAuthority = (category: string) => ["CL", "RH"].includes(category);

  return (
    <Container size="xl" py="xl">
      <Stack gap="lg">
        <div>
          <Title order={2}>Unit Head Reviews</Title>
          <Text c="dimmed" size="sm">
            Review departmental leave applications. CL/RH requests have final approval here;
            higher-sanction requests proceed with your recommendation.
          </Text>
        </div>

        <Card withBorder shadow="xs" radius="md">
          {loading ? (
            <Text p="md">Loading reviews...</Text>
          ) : reviews.length === 0 ? (
            <Text p="xl" ta="center" c="dimmed">
              No leave applications awaiting Unit Head review.
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
                  <Table.Th>Station Leave?</Table.Th>
                  <Table.Th>Substitute Status</Table.Th>
                  <Table.Th>Workflow Action</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {reviews.map((r) => {
                  const finalAuth = isFinalAuthority(r.leave_category);
                  return (
                    <Table.Tr key={r.id}>
                      <Table.Td fw={600}>#{r.id}</Table.Td>
                      <Table.Td>User #{r.user_id}</Table.Td>
                      <Table.Td>
                        <Badge variant="light">{r.leave_category}</Badge>
                      </Table.Td>
                      <Table.Td>
                        {r.start_date} to {r.end_date}
                      </Table.Td>
                      <Table.Td>{r.chargeable_days}</Table.Td>
                      <Table.Td>
                        {r.station_leave ? (
                          <Badge color="orange" size="xs">
                            Yes
                          </Badge>
                        ) : (
                          "No"
                        )}
                      </Table.Td>
                      <Table.Td>
                        {r.substitute_required ? (
                          <Badge
                            color={r.substitute_status === "accepted" ? "teal" : "gray"}
                            size="xs"
                          >
                            {r.substitute_status}
                          </Badge>
                        ) : (
                          "N/A"
                        )}
                      </Table.Td>
                      <Table.Td>
                        {finalAuth ? (
                          <Group gap="xs">
                            <Button
                              size="xs"
                              color="green"
                              onClick={() => {
                                setSelectedApp(r);
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
                                setSelectedApp(r);
                                setActionType("reject");
                                setRemarks("");
                                setOpened(true);
                              }}
                            >
                              Reject
                            </Button>
                          </Group>
                        ) : (
                          <Group gap="xs">
                            <Button
                              size="xs"
                              color="blue"
                              onClick={() => {
                                setSelectedApp(r);
                                setActionType("recommend");
                                setRemarks("");
                                setOpened(true);
                              }}
                            >
                              Recommend
                            </Button>
                            <Button
                              size="xs"
                              color="orange"
                              variant="light"
                              onClick={() => {
                                setSelectedApp(r);
                                setActionType("not_recommend");
                                setRemarks("");
                                setOpened(true);
                              }}
                            >
                              Not Recommend
                            </Button>
                          </Group>
                        )}
                      </Table.Td>
                    </Table.Tr>
                  );
                })}
              </Table.Tbody>
            </Table>
          )}
        </Card>
      </Stack>

      <Modal opened={opened} onClose={() => setOpened(false)} title="Record Unit Head Decision">
        <Stack gap="md">
          <Text size="sm">
            Leave #{selectedApp?.id} ({selectedApp?.leave_category}) from{" "}
            {selectedApp?.start_date} to {selectedApp?.end_date} (
            {selectedApp?.chargeable_days} days).
          </Text>
          <Text size="xs" c="dimmed">
            Reason: {selectedApp?.reason}
          </Text>
          <Textarea
            label="Review Remarks"
            placeholder="Enter reason or comments"
            value={remarks}
            onChange={(e) => setRemarks(e.target.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setOpened(false)}>
              Cancel
            </Button>
            <Button loading={submitting} onClick={handleAction}>
              Confirm {actionType.replace("_", " ").toUpperCase()}
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
};

export default UnitHeadReviewsPage;
