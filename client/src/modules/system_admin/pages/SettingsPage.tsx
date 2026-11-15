import { useState } from "react";
import {
  Button,
  Card,
  Container,
  Group,
  SimpleGrid,
  Stack,
  Switch,
  Text,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCog, FaEdit } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useSystemParameters,
  useUpdateSystemParameter,
} from "../api/hooks";
import { EditParametersModal } from "../components/EditParametersModal";

export default function SettingsPage() {
  const { data, isPending, error } = useSystemParameters();
  const updateParam = useUpdateSystemParameter();

  const [editingKey, setEditingKey] = useState<string | null>(null);

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  // Parse parameters whether returned as map or array
  const params: Record<string, string> = {};
  if (data && typeof data === "object") {
    if (Array.isArray(data)) {
      data.forEach((p: any) => {
        if (p.key) params[p.key] = p.value;
      });
    } else {
      Object.assign(params, data);
    }
  }

  const isMaintenance = params["MAINTENANCE_MODE_ENABLED"] === "true";

  const toggleMaintenance = () => {
    const nextVal = isMaintenance ? "false" : "true";
    updateParam.mutate(
      { key: "MAINTENANCE_MODE_ENABLED", value: nextVal },
      {
        onSuccess: () => {
          notifications.show({
            color: nextVal === "true" ? "orange" : "green",
            title: nextVal === "true" ? "Maintenance Enabled" : "Maintenance Disabled",
            message: `System maintenance mode is now ${nextVal === "true" ? "ACTIVE" : "INACTIVE"}.`,
          });
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Update Failed",
            message: errorMessage(err),
          });
        },
      },
    );
  };

  return (
    <Container size="xl">
      <PageHeader
        title="System Parameters"
        subtitle="Configure dynamic runtime parameters, security thresholds, and maintenance modes"
      />

      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg">
        {/* Maintenance Mode Card */}
        <Card padding="lg" withBorder radius="md">
          <Group justify="space-between" mb="xs">
            <div>
              <Title order={4}>Maintenance Mode</Title>
              <Text size="xs" c="dimmed">
                Restricts non-superadmin access during critical updates
              </Text>
            </div>
            <Switch
              size="lg"
              checked={isMaintenance}
              onChange={toggleMaintenance}
              color="orange"
            />
          </Group>
          <Text size="sm" mt="md">
            Broadcast message:{" "}
            <strong>
              {params["MAINTENANCE_BANNER_MESSAGE"] || "Routine maintenance in progress."}
            </strong>
          </Text>
          <Group mt="md">
            <Button
              size="xs"
              variant="light"
              leftSection={<FaEdit size={10} />}
              onClick={() => setEditingKey("MAINTENANCE_BANNER_MESSAGE")}
            >
              Edit Broadcast Message
            </Button>
          </Group>
        </Card>

        {/* Security Controls Card */}
        <Card padding="lg" withBorder radius="md">
          <Title order={4} mb="xs">
            Security & Session Thresholds
          </Title>
          <Text size="xs" c="dimmed" mb="md">
            Authentication security policies and session lifespans
          </Text>

          <Stack gap="sm">
            <Group justify="space-between">
              <div>
                <Text size="sm">Session Timeout:</Text>
                <Text size="xs" c="dimmed">Inactivity termination window</Text>
              </div>
              <Group gap="xs">
                <Text fw={600} size="sm">
                  {params["SESSION_TIMEOUT_MINUTES"] || "30"} mins
                </Text>
                <Button
                  size="compact-xs"
                  variant="subtle"
                  onClick={() => setEditingKey("SESSION_TIMEOUT_MINUTES")}
                >
                  <FaEdit size={10} />
                </Button>
              </Group>
            </Group>

            <Group justify="space-between">
              <div>
                <Text size="sm">Max Failed Login Attempts:</Text>
                <Text size="xs" c="dimmed">Triggers security alert notification</Text>
              </div>
              <Group gap="xs">
                <Text fw={600} size="sm">
                  {params["MAX_FAILED_LOGIN_ATTEMPTS"] || "5"}
                </Text>
                <Button
                  size="compact-xs"
                  variant="subtle"
                  onClick={() => setEditingKey("MAX_FAILED_LOGIN_ATTEMPTS")}
                >
                  <FaEdit size={10} />
                </Button>
              </Group>
            </Group>
          </Stack>
        </Card>

        {/* Operational Limits Card */}
        <Card padding="lg" withBorder radius="md">
          <Title order={4} mb="xs">
            Operational Governance Limits
          </Title>
          <Text size="xs" c="dimmed" mb="md">
            Safety boundaries on bulk actions and reversible archival
          </Text>

          <Stack gap="sm">
            <Group justify="space-between">
              <div>
                <Text size="sm">Bulk Import Maximum:</Text>
                <Text size="xs" c="dimmed">Cap on batch operations (BR-SA-030)</Text>
              </div>
              <Text fw={600} size="sm">
                1,000 records
              </Text>
            </Group>

            <Group justify="space-between">
              <div>
                <Text size="sm">Archival Reversibility Window:</Text>
                <Text size="xs" c="dimmed">Retention duration before permanent non-restorable</Text>
              </div>
              <Group gap="xs">
                <Text fw={600} size="sm">
                  {params["ARCHIVAL_REVERSIBLE_DAYS"] || "180"} days
                </Text>
                <Button
                  size="compact-xs"
                  variant="subtle"
                  onClick={() => setEditingKey("ARCHIVAL_REVERSIBLE_DAYS")}
                >
                  <FaEdit size={10} />
                </Button>
              </Group>
            </Group>
          </Stack>
        </Card>
      </SimpleGrid>

      {editingKey && (
        <EditParametersModal
          paramKey={editingKey}
          currentValue={params[editingKey] || ""}
          opened={Boolean(editingKey)}
          onClose={() => setEditingKey(null)}
        />
      )}
    </Container>
  );
}
