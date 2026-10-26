import {
  Badge,
  Card,
  Divider,
  Grid,
  Group,
  Modal,
  Stack,
  Text,
  Timeline,
  Title,
} from "@mantine/core";
import { FaCheckCircle, FaClock, FaHistory, FaTimesCircle } from "react-icons/fa";

import { useApplication } from "../api/hooks";

interface Props {
  applicationId: number | null;
  onClose: () => void;
}

export function ApplicationDetailModal({ applicationId, onClose }: Props) {
  const { data: app, isPending } = useApplication(applicationId);

  return (
    <Modal
      opened={!!applicationId}
      onClose={onClose}
      title={<Title order={3}>Leave Application #{applicationId}</Title>}
      size="lg"
      centered
    >
      {isPending || !app ? (
        <Text c="dimmed">Loading application details...</Text>
      ) : (
        <Stack gap="md">
          <Grid>
            <Grid.Col span={6}>
              <Text size="xs" c="dimmed">Leave Category</Text>
              <Text fw={600} size="md">{app.leave_type}</Text>
            </Grid.Col>
            <Grid.Col span={6}>
              <Text size="xs" c="dimmed">Status</Text>
              <Badge color={app.status === "APPROVED" ? "green" : app.status === "REJECTED" ? "red" : "blue"}>
                {app.status}
              </Badge>
            </Grid.Col>

            <Grid.Col span={6}>
              <Text size="xs" c="dimmed">Dates</Text>
              <Text size="sm">{app.start_date} to {app.end_date}</Text>
            </Grid.Col>
            <Grid.Col span={6}>
              <Text size="xs" c="dimmed">Duration</Text>
              <Text size="sm">{app.days_count} day(s) ({app.half_day_type})</Text>
            </Grid.Col>

            <Grid.Col span={12}>
              <Text size="xs" c="dimmed">Reason</Text>
              <Text size="sm">{app.reason}</Text>
            </Grid.Col>

            {app.substitute_user_id && (
              <Grid.Col span={12}>
                <Card withBorder padding="xs" radius="sm">
                  <Text size="xs" c="dimmed">Substitute Coverage</Text>
                  <Text size="sm" fw={500}>
                    Nominated User #{app.substitute_user_id} — Status: {app.substitute_status}
                  </Text>
                  {app.substitute_remarks && (
                    <Text size="xs" c="dimmed">Remarks: {app.substitute_remarks}</Text>
                  )}
                </Card>
              </Grid.Col>
            )}

            {app.is_station_leave && (
              <Grid.Col span={12}>
                <Card withBorder padding="xs" radius="sm">
                  <Text size="xs" c="dimmed">Station Leave Details</Text>
                  <Text size="xs">Departure: {app.station_departure_date ?? "N/A"}</Text>
                  <Text size="xs">Arrival: {app.station_arrival_date ?? "N/A"}</Text>
                  <Text size="xs">Address: {app.station_address || "N/A"}</Text>
                  <Text size="xs">Contact: {app.contact_number || "N/A"}</Text>
                </Card>
              </Grid.Col>
            )}
          </Grid>

          <Divider label="Audit Trail & Lifecycle History" labelPosition="center" />

          {app.action_logs && app.action_logs.length > 0 ? (
            <Timeline active={app.action_logs.length - 1} bulletSize={22} lineWidth={2}>
              {app.action_logs.map((log) => {
                const isApproved = log.action.includes("APPROV") || log.to_status === "APPROVED";
                const isRejected = log.action.includes("REJECT") || log.to_status === "REJECTED";
                const color = isApproved ? "green" : isRejected ? "red" : "blue";
                const Icon = isApproved ? FaCheckCircle : isRejected ? FaTimesCircle : FaClock;

                return (
                  <Timeline.Item
                    key={log.id}
                    bullet={<Icon size={12} />}
                    color={color}
                    title={<Text fw={500} size="sm">{log.action}</Text>}
                  >
                    <Text c="dimmed" size="xs">
                      {log.from_status} → {log.to_status} | User #{log.actor_user_id}
                    </Text>
                    {log.remarks && (
                      <Text size="xs" mt={2}>
                        "{log.remarks}"
                      </Text>
                    )}
                    <Text size="xs" c="dimmed" mt={2}>
                      {new Date(log.created_at).toLocaleString()}
                    </Text>
                  </Timeline.Item>
                );
              })}
            </Timeline>
          ) : (
            <Group justify="center" p="sm">
              <FaHistory color="gray" />
              <Text size="xs" c="dimmed">No action logs recorded yet.</Text>
            </Group>
          )}
        </Stack>
      )}
    </Modal>
  );
}
