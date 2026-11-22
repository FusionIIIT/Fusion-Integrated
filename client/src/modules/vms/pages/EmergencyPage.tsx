import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCheckCircle, FaExclamationCircle, FaExclamationTriangle, FaUsers } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useEmergencyRoster, useRollCall, useTriggerMuster } from "../api/hooks";
import type { EmergencyRosterItem } from "../api/types";

export default function EmergencyPage() {
  const { data: musterData, isPending, error } = useEmergencyRoster();
  const triggerMuster = useTriggerMuster();
  const rollCall = useRollCall();

  const [triggerOpen, setTriggerOpen] = useState(false);
  const [assemblyPoint, setAssemblyPoint] = useState("Central Ground");

  if (error)
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );

  const summary = musterData?.summary ?? { total: 0, accounted: 0, unaccounted: 0 };
  const roster = musterData?.roster ?? [];

  function handleTriggerSubmit() {
    triggerMuster.mutate(
      { assembly_point: assemblyPoint },
      {
        onSuccess: (res) => {
          notifications.show({
            color: "red",
            title: "Emergency Muster Triggered",
            message: `Snapshot created with ID ${res.muster_id}.`,
          });
          setTriggerOpen(false);
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Muster Failed",
            message: errorMessage(err),
          });
        },
      }
    );
  }

  function handleMarkAccounted(item: EmergencyRosterItem) {
    rollCall.mutate(
      { id: item.id, status: "ACCOUNTED" },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Accounted",
            message: `${item.visitor.name} marked as accounted for.`,
          });
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Roll-call Failed",
            message: errorMessage(err),
          });
        },
      }
    );
  }

  return (
    <Container size="xl">
      <Stack gap="lg">
        <PageHeader
          title="Emergency Evacuation Muster Roster"
          subtitle="Snapshot on-site visitors in an emergency and conduct rapid roll-call accountability."
          action={
            <Button
              leftSection={<FaExclamationTriangle />}
              color="red"
              onClick={() => setTriggerOpen(true)}
            >
              Trigger Evacuation Muster
            </Button>
          }
        />

        {/* Accountability Metrics */}
        <SimpleGrid cols={{ base: 1, sm: 3 }}>
          <Card withBorder padding="md" radius="md">
            <Group justify="space-between">
              <div>
                <Text size="xs" c="dimmed" fw={700}>
                  TOTAL ON-SITE
                </Text>
                <Text fw={700} size="xl">
                  {summary.total}
                </Text>
              </div>
              <FaUsers size={24} color="var(--mantine-color-blue-6)" />
            </Group>
          </Card>
          <Card withBorder padding="md" radius="md">
            <Group justify="space-between">
              <div>
                <Text size="xs" c="dimmed" fw={700}>
                  ACCOUNTED FOR
                </Text>
                <Text fw={700} size="xl" c="green">
                  {summary.accounted}
                </Text>
              </div>
              <FaCheckCircle size={24} color="var(--mantine-color-green-6)" />
            </Group>
          </Card>
          <Card withBorder padding="md" radius="md">
            <Group justify="space-between">
              <div>
                <Text size="xs" c="dimmed" fw={700}>
                  UNACCOUNTED
                </Text>
                <Text fw={700} size="xl" c="red">
                  {summary.unaccounted}
                </Text>
              </div>
              <FaExclamationCircle size={24} color="var(--mantine-color-red-6)" />
            </Group>
          </Card>
        </SimpleGrid>

        <DataTable
          loading={isPending}
          rows={roster}
          rowKey={(r) => r.id}
          empty={{ title: "No active emergency muster in progress." }}
          columns={[
            {
              key: "name",
              header: "Visitor Name",
              render: (r: EmergencyRosterItem) => (
                <Stack gap={2}>
                  <Text fw={600}>{r.visitor.name}</Text>
                  <Text size="xs" c="dimmed">
                    {r.visitor.phone}
                  </Text>
                </Stack>
              ),
            },
            {
              key: "checkin",
              header: "Check-in Time",
              render: (r: EmergencyRosterItem) => new Date(r.check_in_time).toLocaleTimeString(),
            },
            {
              key: "assembly",
              header: "Assembly Point",
              render: (r: EmergencyRosterItem) => r.assembly_point,
            },
            {
              key: "status",
              header: "Accountability",
              render: (r: EmergencyRosterItem) => (
                <Badge color={r.accountability_status === "ACCOUNTED" ? "green" : "red"}>
                  {r.accountability_status}
                </Badge>
              ),
            },
            {
              key: "action",
              header: "Action",
              render: (r: EmergencyRosterItem) =>
                r.accountability_status === "UNACCOUNTED" ? (
                  <Button
                    size="xs"
                    color="green"
                    variant="light"
                    leftSection={<FaCheckCircle />}
                    loading={rollCall.isPending}
                    onClick={() => handleMarkAccounted(r)}
                  >
                    Mark Accounted
                  </Button>
                ) : (
                  <Text size="xs" c="dimmed">
                    Verified {r.accounted_at ? new Date(r.accounted_at).toLocaleTimeString() : ""}
                  </Text>
                ),
            },
          ]}
        />

        {/* Modal: Trigger Muster */}
        <Modal
          opened={triggerOpen}
          onClose={() => setTriggerOpen(false)}
          title="Trigger Emergency Evacuation Muster"
          size="sm"
        >
          <Stack gap="sm">
            <Text size="sm">
              This will snapshot all on-site visitors into an emergency roll-call roster.
            </Text>
            <TextInput
              label="Designated Assembly Point"
              required
              value={assemblyPoint}
              onChange={(e) => setAssemblyPoint(e.target.value)}
            />
            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => setTriggerOpen(false)}>
                Cancel
              </Button>
              <Button color="red" loading={triggerMuster.isPending} onClick={handleTriggerSubmit}>
                Confirm Evacuation Muster
              </Button>
            </Group>
          </Stack>
        </Modal>
      </Stack>
    </Container>
  );
}
