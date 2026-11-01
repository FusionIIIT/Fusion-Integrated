import { useState } from "react";
import {
  Modal,
  TextInput,
  Stack,
  Button,
  Group,
  Text,
  Alert,
  PasswordInput,
} from "@mantine/core";
import { useUpdateConfiguration } from "../api/hooks";
import type { ConfigItem } from "../api/types";
import { errorMessage } from "../../../lib/http";

export function EditConfigModal({
  config,
  opened,
  onClose,
}: {
  config: ConfigItem;
  opened: boolean;
  onClose: () => void;
}) {
  const [value, setValue] = useState(
    typeof config.value === "object" ? JSON.stringify(config.value) : String(config.value)
  );
  const [token, setToken] = useState("");
  const [error, setError] = useState<string | null>(null);

  const updateMutation = useUpdateConfiguration(config.key);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    let parsedVal: unknown = value;
    if (config.type === "int") {
      parsedVal = parseInt(value, 10);
    } else if (config.type === "bool") {
      parsedVal = value.toLowerCase() === "true" || value === "1";
    } else if (config.type === "list") {
      try {
        parsedVal = JSON.parse(value);
      } catch {
        parsedVal = value.split(",").map((s) => s.trim());
      }
    }

    try {
      await updateMutation.mutateAsync({
        value: parsedVal,
        confirmation_token: token,
      });
      onClose();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  return (
    <Modal opened={opened} onClose={onClose} title={`Configure Parameter: ${config.key}`} size="md">
      <form onSubmit={handleSubmit}>
        <Stack gap="sm">
          {error && <Alert color="red">{error}</Alert>}
          <Text size="xs" c="dimmed">
            Category: {config.category.toUpperCase()} | Type: {config.type}
          </Text>
          <TextInput
            label="Parameter Value"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            required
          />
          {config.is_critical && (
            <PasswordInput
              label="Re-authentication PIN / Credential (Critical Parameter)"
              placeholder="Enter PIN to confirm"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              required
            />
          )}
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={onClose}>Cancel</Button>
            <Button type="submit" loading={updateMutation.isPending}>Save Parameter</Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
