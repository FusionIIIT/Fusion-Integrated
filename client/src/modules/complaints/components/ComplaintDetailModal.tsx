import {
  Alert,
  Badge,
  Box,
  Card,
  Divider,
  Grid,
  Group,
  Loader,
  Modal,
  Stack,
  Text,
  Timeline,
  Title,
} from "@mantine/core";
import dayjs from "dayjs";
import { FaCheckCircle, FaExclamationTriangle, FaFileAlt, FaHistory, FaStar } from "react-icons/fa";

import { useComplaint } from "../api/hooks";
import { PriorityBadge } from "./PriorityBadge";
import { StatusBadge } from "./StatusBadge";

interface Props {
  complaintId: number | string | null;
  opened: boolean;
  onClose: () => void;
}

export function ComplaintDetailModal({ complaintId, opened, onClose }: Props) {
  const { data: complaint, isLoading, error } = useComplaint(complaintId || undefined);

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={
        <Group>
          <Title order={4}>Complaint Details</Title>
          {complaint && <Badge variant="outline">{complaint.complaint_id}</Badge>}
        </Group>
      }
      size="lg"
    >
      {isLoading && (
        <Stack align="center" py="xl">
          <Loader size="md" />
          <Text size="sm" c="dimmed">
            Loading complaint details...
          </Text>
        </Stack>
      )}

      {error && (
        <Alert color="red" title="Error loading complaint">
          Unable to fetch complaint details. Please try again.
        </Alert>
      )}

      {complaint && (
        <Stack gap="md">
          <Grid>
            <Grid.Col span={6}>
              <Text size="xs" c="dimmed">
                Status & Priority
              </Text>
              <Group gap="xs" mt={4}>
                <StatusBadge status={complaint.status} isEscalated={complaint.is_escalated} />
                <PriorityBadge priority={complaint.priority} />
              </Group>
            </Grid.Col>
            <Grid.Col span={6}>
              <Text size="xs" c="dimmed">
                Category
              </Text>
              <Text size="sm" fw={500}>
                {complaint.category?.name || complaint.category_name}
              </Text>
            </Grid.Col>

            <Grid.Col span={6}>
              <Text size="xs" c="dimmed">
                Location
              </Text>
              <Text size="sm">{complaint.location}</Text>
            </Grid.Col>
            <Grid.Col span={6}>
              <Text size="xs" c="dimmed">
                Assigned Worker
              </Text>
              <Text size="sm">{complaint.assigned_worker_name || "Unassigned"}</Text>
            </Grid.Col>

            <Grid.Col span={6}>
              <Text size="xs" c="dimmed">
                Submitted At
              </Text>
              <Text size="sm">{dayjs(complaint.created_at).format("DD MMM YYYY, hh:mm A")}</Text>
            </Grid.Col>
            <Grid.Col span={6}>
              <Text size="xs" c="dimmed">
                SLA Deadline
              </Text>
              <Text size="sm" c={complaint.is_escalated ? "red" : undefined}>
                {complaint.sla_deadline
                  ? dayjs(complaint.sla_deadline).format("DD MMM YYYY, hh:mm A")
                  : "N/A"}
              </Text>
            </Grid.Col>
          </Grid>

          <Box>
            <Text size="xs" c="dimmed">
              Description
            </Text>
            <Card withBorder p="sm" mt={4} radius="sm" bg="gray.0">
              <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                {complaint.description}
              </Text>
            </Card>
          </Box>

          {complaint.resolution_details && (
            <Alert color="teal" icon={<FaCheckCircle />} title="Resolution Details">
              <Text size="sm">{complaint.resolution_details}</Text>
              {complaint.resolved_at && (
                <Text size="xs" c="dimmed" mt={4}>
                  Resolved on: {dayjs(complaint.resolved_at).format("DD MMM YYYY, hh:mm A")}
                </Text>
              )}
            </Alert>
          )}

          {complaint.rejection_reason && (
            <Alert color="red" icon={<FaExclamationTriangle />} title="Rejection Reason">
              <Text size="sm">{complaint.rejection_reason}</Text>
              {complaint.rejected_at && (
                <Text size="xs" c="dimmed" mt={4}>
                  Rejected on: {dayjs(complaint.rejected_at).format("DD MMM YYYY, hh:mm A")}
                </Text>
              )}
            </Alert>
          )}

          {complaint.is_escalated && (
            <Alert color="red" icon={<FaExclamationTriangle />} title="Escalation Remarks">
              <Text size="sm">{complaint.escalation_remarks || "Escalated for supervisory review."}</Text>
              <Text size="xs" c="dimmed" mt={4}>
                Type: {complaint.escalation_type} | Escalated at:{" "}
                {complaint.escalated_at
                  ? dayjs(complaint.escalated_at).format("DD MMM YYYY, hh:mm A")
                  : "N/A"}
              </Text>
            </Alert>
          )}

          {complaint.reopening_status !== "none" && (
            <Alert color="orange" title={`Reopening Status: ${complaint.reopening_status.toUpperCase()}`}>
              <Text size="sm">
                <strong>Reason:</strong> {complaint.reopening_reason}
              </Text>
              {complaint.reopening_review_remarks && (
                <Text size="sm" mt={4}>
                  <strong>Review Remarks:</strong> {complaint.reopening_review_remarks}
                </Text>
              )}
            </Alert>
          )}

          {complaint.feedback && (
            <Alert color="yellow" icon={<FaStar />} title="Complainant Feedback">
              <Group gap="xs">
                <Badge color="yellow" variant="filled">
                  ★ {complaint.feedback.rating} / 5
                </Badge>
              </Group>
              {complaint.feedback.comments && (
                <Text size="sm" mt={4}>
                  "{complaint.feedback.comments}"
                </Text>
              )}
            </Alert>
          )}

          {complaint.attachments && complaint.attachments.length > 0 && (
            <Box>
              <Text size="xs" c="dimmed" mb={4}>
                Attachments ({complaint.attachments.length})
              </Text>
              <Stack gap="xs">
                {complaint.attachments.map((att) => (
                  <Card key={att.id} withBorder p="xs" radius="sm">
                    <Group justify="space-between">
                      <Group gap="xs">
                        <FaFileAlt color="#666" />
                        <Text size="sm">{att.file_name}</Text>
                      </Group>
                      <Text size="xs" c="dimmed">
                        {Math.round(att.file_size / 1024)} KB
                      </Text>
                    </Group>
                  </Card>
                ))}
              </Stack>
            </Box>
          )}

          <Divider my="xs" />

          <Box>
            <Group gap="xs" mb="sm">
              <FaHistory color="#888" />
              <Title order={5}>Lifecycle History & Audit Trail</Title>
            </Group>
            {complaint.transitions && complaint.transitions.length > 0 ? (
              <Timeline active={complaint.transitions.length - 1} bulletSize={20} lineWidth={2}>
                {complaint.transitions.map((tr) => (
                  <Timeline.Item
                    key={tr.id}
                    title={
                      <Group gap="xs">
                        <Badge size="xs" variant="outline">
                          {tr.to_status}
                        </Badge>
                        <Text size="xs" c="dimmed">
                          by {tr.actor_role} ({dayjs(tr.created_at).format("DD MMM, hh:mm A")})
                        </Text>
                      </Group>
                    }
                  >
                    <Text size="sm" c="dimmed">
                      {tr.remarks || "State transition recorded."}
                    </Text>
                  </Timeline.Item>
                ))}
              </Timeline>
            ) : (
              <Text size="sm" c="dimmed">
                No transition records yet.
              </Text>
            )}
          </Box>
        </Stack>
      )}
    </Modal>
  );
}
