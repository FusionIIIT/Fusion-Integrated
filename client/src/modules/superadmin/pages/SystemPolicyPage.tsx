import { useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Group,
  Loader,
  Modal,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";

import { useSystemParameters, useUpdateSystemParameter } from "../api/hooks";
import type { SystemParameter } from "../api/types";

export default function SystemPolicyPage() {
  const { data: parameters, isLoading, isError } = useSystemParameters();
  const [modalOpened, setModalOpened] = useState(false);
  const [paramKey, setParamKey] = useState("");
  const [paramVal, setParamVal] = useState("");

  const updateMutation = useUpdateSystemParameter();

  const handleSave = () => {
    updateMutation.mutate(
      {
        parameter_key: paramKey,
        parameter_value: { value: isNaN(Number(paramVal)) ? paramVal : Number(paramVal) },
      },
      {
        onSuccess: () => {
          setModalOpened(false);
          setParamKey("");
          setParamVal("");
        },
      },
    );
  };

  return (
    <Stack gap="lg" p="md">
      <Group justify="space-between">
        <div>
          <Title order={2}>System Parameter Policies</Title>
          <Text c="dimmed">Versioned, effective-dated institutional governance parameters (BR-SA-035).</Text>
        </div>
        <Button onClick={() => setModalOpened(true)}>Configure Parameter</Button>
      </Group>

      {isLoading && (
        <Stack align="center" justify="center" p="xl" data-testid="loading-spinner">
          <Loader size="lg" />
          <Text c="dimmed">Loading system parameters...</Text>
        </Stack>
      )}

      {isError && (
        <Alert color="red" title="Error loading parameters" data-testid="error-message">
          Failed to retrieve system parameters from the server.
        </Alert>
      )}

      {!isLoading && !isError && parameters?.length === 0 && (
        <Alert color="blue" title="No parameters configured" data-testid="empty-message">
          No system parameters configured.
        </Alert>
      )}

      {!isLoading && !isError && parameters && parameters.length > 0 && (
        <Table withTableBorder striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Parameter Key</Table.Th>
              <Table.Th>Configured Value</Table.Th>
              <Table.Th>Version</Table.Th>
              <Table.Th>Effective From</Table.Th>
              <Table.Th>Status</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {parameters.map((p: SystemParameter) => (
              <Table.Tr key={p.id}>
                <Table.Td fw={500}>{p.parameter_key}</Table.Td>
                <Table.Td>{JSON.stringify(p.parameter_value)}</Table.Td>
                <Table.Td>v{p.version}</Table.Td>
                <Table.Td>{new Date(p.effective_from).toLocaleDateString()}</Table.Td>
                <Table.Td>
                  <Badge color={p.is_active ? "green" : "gray"}>
                    {p.is_active ? "Active" : "Superseded"}
                  </Badge>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}

      <Modal opened={modalOpened} onClose={() => setModalOpened(false)} title="Configure System Parameter">
        <Stack gap="sm">
          <TextInput
            label="Parameter Key"
            placeholder="e.g. REVERSIBILITY_WINDOW_DAYS"
            value={paramKey}
            onChange={(e) => setParamKey(e.currentTarget.value)}
            required
          />
          <TextInput
            label="Value"
            placeholder="e.g. 90"
            value={paramVal}
            onChange={(e) => setParamVal(e.currentTarget.value)}
            required
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setModalOpened(false)}>Cancel</Button>
            <Button onClick={handleSave} loading={updateMutation.isPending}>Save Parameter</Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}
