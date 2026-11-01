import { useState } from "react";
import {
  Alert,
  Button,
  Card,
  Group,
  Modal,
  NumberInput,
  Stack,
  Table,
  Text,
  Textarea,
  TextInput,
} from "@mantine/core";
import {
  FaCheck,
  FaCogs,
  FaEdit,
  FaExclamationTriangle,
  FaInfoCircle,
} from "react-icons/fa";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useSystemConfig, useUpdateSystemConfig } from "../api/hooks";

const PARAM_METADATA: Record<
  string,
  { label: string; description: string; range: string; min?: number; max?: number }
> = {
  session_timeout_minutes: {
    label: "Super Admin Session Inactivity Timeout",
    description: "Period of inactivity after which an operator session is terminated automatically.",
    range: "5 – 60 minutes",
    min: 5,
    max: 60,
  },
  reversibility_window_days: {
    label: "Archived User Reversibility Window",
    description: "Days during which an archived user may be restored to active status.",
    range: "30 – 365 days",
    min: 30,
    max: 365,
  },
  role_reminder_intervals_days: {
    label: "Role Expiry Reminder Intervals",
    description: "Lead intervals (in days) prior to expiration when reminder notifications are dispatched.",
    range: "Comma-separated days, e.g. 15, 7, 1",
  },
  failed_login_alert_threshold: {
    label: "Failed Login Security Alert Threshold",
    description: "Consecutive failed login attempts that trigger security warning notifications.",
    range: "3 – 10 attempts",
    min: 3,
    max: 10,
  },
  purge_retention_years: {
    label: "Archival Minimum Retention Period",
    description: "Minimum elapsed years before archived data is eligible for permanent purge.",
    range: "1 – 25 years",
    min: 1,
    max: 25,
  },
  password_history_count: {
    label: "Password Rotation History Depth",
    description: "Number of past passwords remembered to prevent immediate reuse.",
    range: "1 – 10 passwords",
    min: 1,
    max: 10,
  },
};

export default function SystemConfigPage() {
  const { data: configs = {}, isLoading } = useSystemConfig();
  const updateMutation = useUpdateSystemConfig();

  const [editKey, setEditKey] = useState<string | null>(null);
  const [numValue, setNumValue] = useState<number | "">("");
  const [textValue, setTextValue] = useState("");
  const [editDesc, setEditDesc] = useState("");

  const handleOpenEdit = (key: string, val: unknown) => {
    setEditKey(key);
    if (typeof val === "number") {
      setNumValue(val);
      setTextValue("");
    } else if (Array.isArray(val)) {
      setNumValue("");
      setTextValue(val.join(", "));
    } else {
      setNumValue("");
      setTextValue(String(val));
    }
    setEditDesc(PARAM_METADATA[key]?.description || "");
  };

  const handleSave = async () => {
    if (!editKey) return;

    let finalVal: unknown;
    if (editKey === "role_reminder_intervals_days") {
      finalVal = textValue
        .split(",")
        .map((s) => s.trim())
        .filter((s) => s && !isNaN(Number(s)))
        .map(Number);
    } else if (typeof numValue === "number") {
      finalVal = numValue;
    } else {
      finalVal = textValue;
    }

    try {
      await updateMutation.mutateAsync({
        key: editKey,
        value: finalVal,
        description: editDesc,
      });
      setEditKey(null);
    } catch {
      // Handled
    }
  };

  return (
    <Stack gap="lg">
      <PageHeader
        title="System-Wide Configuration Parameters"
        subtitle="Manage permitted administrative threshold and policy parameters (CFR-SA-023, BR-SA-035)"
      />

      <Alert color="blue" icon={<FaInfoCircle />}>
        Super Admin configuration authority is strictly bounded by institutional policy (BR-SA-035). Only allocated lifecycle parameters may be modified here.
      </Alert>

      <Card withBorder p="md" radius="md">
        <Table highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Parameter</Table.Th>
              <Table.Th>Current Value</Table.Th>
              <Table.Th>Permitted Boundary</Table.Th>
              <Table.Th style={{ textAlign: "right" }}>Edit</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {Object.keys(PARAM_METADATA).map((key) => {
              const meta = PARAM_METADATA[key];
              const val = configs[key];
              const displayVal = Array.isArray(val) ? val.join(", ") : String(val ?? "Default");

              return (
                <Table.Tr key={key}>
                  <Table.Td>
                    <Text fw={600} size="sm">
                      {meta.label}
                    </Text>
                    <Text size="xs" c="dimmed">
                      {meta.description}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Text fw={700} size="sm">
                      {displayVal}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Text size="xs" c="dimmed">
                      {meta.range}
                    </Text>
                  </Table.Td>
                  <Table.Td style={{ textAlign: "right" }}>
                    <Button
                      size="xs"
                      variant="subtle"
                      leftSection={<FaEdit size={12} />}
                      onClick={() => handleOpenEdit(key, val)}
                    >
                      Modify
                    </Button>
                  </Table.Td>
                </Table.Tr>
              );
            })}
          </Table.Tbody>
        </Table>
      </Card>

      {/* Edit Parameter Modal */}
      <Modal opened={!!editKey} onClose={() => setEditKey(null)} title="Modify System Parameter" size="md">
        {editKey && (
          <Stack gap="sm">
            <Text fw={600} size="sm">
              {PARAM_METADATA[editKey]?.label}
            </Text>
            <Text size="xs" c="dimmed">
              Permitted constraint: {PARAM_METADATA[editKey]?.range}
            </Text>

            {editKey === "role_reminder_intervals_days" ? (
              <TextInput
                label="Intervals (Days, comma-separated)"
                value={textValue}
                onChange={(e) => setTextValue(e.currentTarget.value)}
                placeholder="15, 7, 1"
              />
            ) : (
              <NumberInput
                label="Value"
                value={numValue}
                onChange={setNumValue}
                min={PARAM_METADATA[editKey]?.min}
                max={PARAM_METADATA[editKey]?.max}
              />
            )}

            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => setEditKey(null)}>
                Cancel
              </Button>
              <Button onClick={handleSave} loading={updateMutation.isPending}>
                Save Parameter
              </Button>
            </Group>
          </Stack>
        )}
      </Modal>
    </Stack>
  );
}
