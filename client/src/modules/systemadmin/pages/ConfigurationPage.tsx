import { useState } from "react";
import {
  Stack,
  Table,
  Badge,
  Text,
  Button,
  Paper,
  Loader,
  Alert,
  Tooltip,
} from "@mantine/core";
import {
  FaShieldAlt,
  FaEdit,
  FaLock,
} from "react-icons/fa";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useConfigurations } from "../api/hooks";
import type { ConfigItem } from "../api/types";
import { EditConfigModal } from "../components/ConfigModal";

export default function ConfigurationPage() {
  const { data, isLoading, error } = useConfigurations();
  const [selectedConfig, setSelectedConfig] = useState<ConfigItem | null>(null);

  const getCategoryBadge = (category: string) => {
    switch (category) {
      case "security":
        return <Badge color="red">Security</Badge>;
      case "session":
        return <Badge color="indigo">Session</Badge>;
      case "user_policy":
        return <Badge color="teal">User Policy</Badge>;
      case "archival":
        return <Badge color="orange">Archival</Badge>;
      case "role":
        return <Badge color="blue">Role Lifecycle</Badge>;
      default:
        return <Badge color="gray">{category}</Badge>;
    }
  };

  return (
    <Stack gap="lg">
      <PageHeader
        title="System Configuration"
        subtitle="Manage permitted institutional parameters and system thresholds"
      />

      {/* Operational Boundary Alert (BR-SA-035) */}
      <Alert
        icon={<FaShieldAlt size={16} />}
        title="Strict Operational Boundary Enforced (BR-SA-035)"
        color="indigo"
        radius="md"
      >
        System Administrators are restricted to control plane operations (session timeouts, password policies, retention schedules, alert thresholds). Modification of module-specific business rules, academic grades, examination structures, or leave formulas is strictly prohibited and cryptographically blocked.
      </Alert>

      {isLoading && (
        <Stack align="center" justify="center" p="xl">
          <Loader />
          <Text c="dimmed">Loading system parameters...</Text>
        </Stack>
      )}

      {error && (
        <Alert color="red" title="Error">
          Failed to load system configuration parameters.
        </Alert>
      )}

      {data && (
        <Paper withBorder radius="md">
          <Table verticalSpacing="sm" striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Parameter Key</Table.Th>
                <Table.Th>Category</Table.Th>
                <Table.Th>Description</Table.Th>
                <Table.Th>Current Value</Table.Th>
                <Table.Th>Criticality</Table.Th>
                <Table.Th>Last Modified By</Table.Th>
                <Table.Th style={{ width: 100, textAlign: "center" }}>Actions</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {data.results.map((cfg) => (
                <Table.Tr key={cfg.key}>
                  <Table.Td>
                    <Text fw={600} ff="monospace">
                      {cfg.key}
                    </Text>
                  </Table.Td>
                  <Table.Td>{getCategoryBadge(cfg.category)}</Table.Td>
                  <Table.Td>
                    <Text size="sm">{cfg.description || "—"}</Text>
                  </Table.Td>
                  <Table.Td>
                    <Badge variant="outline" color="dark" size="lg">
                      {typeof cfg.value === "object"
                        ? JSON.stringify(cfg.value)
                        : String(cfg.value)}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    {cfg.is_critical ? (
                      <Tooltip label="Requires step-up confirmation PIN (BR-SA-030)">
                        <Badge color="red" leftSection={<FaLock size={10} />}>
                          Critical
                        </Badge>
                      </Tooltip>
                    ) : (
                      <Badge color="gray">Standard</Badge>
                    )}
                  </Table.Td>
                  <Table.Td>
                    <Text size="xs" c="dimmed">
                      {cfg.updated_by || "System Initial"}
                    </Text>
                  </Table.Td>
                  <Table.Td style={{ textAlign: "center" }}>
                    <Button
                      size="xs"
                      variant="light"
                      leftSection={<FaEdit size={12} />}
                      onClick={() => setSelectedConfig(cfg)}
                    >
                      Edit
                    </Button>
                  </Table.Td>
                </Table.Tr>
              ))}
              {data.results.length === 0 && (
                <Table.Tr>
                  <Table.Td colSpan={7} style={{ textAlign: "center", padding: "2rem" }}>
                    <Text c="dimmed">No configuration parameters registered.</Text>
                  </Table.Td>
                </Table.Tr>
              )}
            </Table.Tbody>
          </Table>
        </Paper>
      )}

      {selectedConfig && (
        <EditConfigModal
          config={selectedConfig}
          opened={Boolean(selectedConfig)}
          onClose={() => setSelectedConfig(null)}
        />
      )}
    </Stack>
  );
}
