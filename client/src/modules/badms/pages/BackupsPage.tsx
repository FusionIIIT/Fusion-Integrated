import { useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  Select,
  Stack,
  Table,
  Tabs,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import {
  FaCheckCircle,
  FaExclamationCircle,
  FaHdd,
  FaPlay,
  FaPlus,
  FaShieldAlt,
} from "react-icons/fa";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useBackupSchedules,
  useBackups,
  useRunScheduledBackup,
  useTriggerBackup,
  useVerifyBackupIntegrity,
} from "../api";
import type { BackupExecution, BackupSchedule } from "../api";

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 MB";
  const mb = bytes / (1024 * 1024);
  if (mb >= 1024) {
    return `${(mb / 1024).toFixed(2)} GB`;
  }
  return `${mb.toFixed(1)} MB`;
}

function getStatusBadge(status: string) {
  switch (status) {
    case "completed":
      return <Badge color="green">Completed</Badge>;
    case "failed":
      return <Badge color="red">Failed</Badge>;
    case "in_progress":
      return <Badge color="yellow">In Progress</Badge>;
    default:
      return <Badge color="gray">{status}</Badge>;
  }
}

export default function BackupsPage() {
  const { data: backupsData, isLoading: backupsLoading } = useBackups();
  const { data: schedulesData, isLoading: schedulesLoading } = useBackupSchedules();
  const triggerBackup = useTriggerBackup();
  const verifyIntegrity = useVerifyBackupIntegrity();
  const runSchedule = useRunScheduledBackup();

  const [triggerModalOpen, setTriggerModalOpen] = useState(false);
  const [scope, setScope] = useState<"local" | "global">("local");
  const [dataset, setDataset] = useState("all");
  const [feedbackMsg, setFeedbackMsg] = useState<{ text: string; error?: boolean } | null>(null);

  const backups: BackupExecution[] = backupsData?.results || [];
  const schedules: BackupSchedule[] = schedulesData?.results || [];

  const handleTrigger = async () => {
    setFeedbackMsg(null);
    try {
      await triggerBackup.mutateAsync({
        scope,
        target_dataset: dataset.trim() || "all",
      });
      setTriggerModalOpen(false);
      setFeedbackMsg({ text: `Backup (${scope}) triggered successfully!` });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to trigger backup";
      setFeedbackMsg({ text: msg, error: true });
    }
  };

  const handleVerify = async (id: number) => {
    try {
      await verifyIntegrity.mutateAsync(id);
      setFeedbackMsg({ text: `Backup #${id} integrity verified successfully.` });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Verification failed";
      setFeedbackMsg({ text: msg, error: true });
    }
  };

  const handleRunSchedule = async (id: number) => {
    try {
      await runSchedule.mutateAsync(id);
      setFeedbackMsg({ text: `Scheduled backup #${id} executed.` });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Execution failed";
      setFeedbackMsg({ text: msg, error: true });
    }
  };

  return (
    <Container size="xl" py="md">
      <PageHeader
        title="Backup Management & Schedules"
        subtitle="Trigger manual backups, verify repository reachability and SHA-256 integrity, manage automated schedules"
      />

      <Stack gap="lg" mt="md">
        {feedbackMsg && (
          <Alert
            color={feedbackMsg.error ? "red" : "green"}
            icon={feedbackMsg.error ? <FaExclamationCircle /> : <FaCheckCircle />}
            withCloseButton
            onClose={() => setFeedbackMsg(null)}
          >
            {feedbackMsg.text}
          </Alert>
        )}

        <Group justify="flex-end">
          <Button leftSection={<FaPlus />} onClick={() => setTriggerModalOpen(true)}>
            Trigger Manual Backup
          </Button>
        </Group>

        <Tabs defaultValue="history">
          <Tabs.List>
            <Tabs.Tab value="history" leftSection={<FaHdd />}>
              Execution History ({backups.length})
            </Tabs.Tab>
            <Tabs.Tab value="schedules" leftSection={<FaPlay />}>
              Automated Schedules ({schedules.length})
            </Tabs.Tab>
          </Tabs.List>

          {/* Backup History Tab */}
          <Tabs.Panel value="history" pt="md">
            <Card padding="lg" withBorder radius="md">
              <Title order={4} mb="md">
                Backup Executions
              </Title>

              {backupsLoading ? (
                <Text c="dimmed">Loading backup records...</Text>
              ) : backups.length === 0 ? (
                <Text c="dimmed">No backup executions recorded yet.</Text>
              ) : (
                <Table highlightOnHover withTableBorder>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>ID</Table.Th>
                      <Table.Th>Scope / Type</Table.Th>
                      <Table.Th>Target Dataset</Table.Th>
                      <Table.Th>Status</Table.Th>
                      <Table.Th>Size</Table.Th>
                      <Table.Th>Repository Reachable</Table.Th>
                      <Table.Th>Integrity</Table.Th>
                      <Table.Th>Started At</Table.Th>
                      <Table.Th>Actions</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {backups.map((b) => (
                      <Table.Tr key={b.id}>
                        <Table.Td fw={600}>#{b.id}</Table.Td>
                        <Table.Td>
                          <Badge variant="outline" color={b.scope === "global" ? "grape" : "blue"}>
                            {b.scope} / {b.backup_type}
                          </Badge>
                        </Table.Td>
                        <Table.Td>{b.target_dataset}</Table.Td>
                        <Table.Td>{getStatusBadge(b.status)}</Table.Td>
                        <Table.Td>{formatBytes(b.size_bytes)}</Table.Td>
                        <Table.Td>
                          {b.repository_reachable ? (
                            <Badge color="green">Reachable</Badge>
                          ) : (
                            <Badge color="red">Unreachable</Badge>
                          )}
                        </Table.Td>
                        <Table.Td>
                          {b.integrity_verified ? (
                            <Badge color="teal" leftSection={<FaShieldAlt size={10} />}>
                              Verified
                            </Badge>
                          ) : (
                            <Badge color="gray">Unverified</Badge>
                          )}
                        </Table.Td>
                        <Table.Td>
                          <Text size="xs">{new Date(b.started_at).toLocaleString()}</Text>
                        </Table.Td>
                        <Table.Td>
                          {b.status === "completed" && (
                            <Button
                              size="xs"
                              variant="light"
                              leftSection={<FaShieldAlt size={12} />}
                              loading={verifyIntegrity.isPending}
                              onClick={() => handleVerify(b.id)}
                            >
                              Verify
                            </Button>
                          )}
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              )}
            </Card>
          </Tabs.Panel>

          {/* Schedules Tab */}
          <Tabs.Panel value="schedules" pt="md">
            <Card padding="lg" withBorder radius="md">
              <Title order={4} mb="md">
                Configured Schedules
              </Title>

              {schedulesLoading ? (
                <Text c="dimmed">Loading schedules...</Text>
              ) : schedules.length === 0 ? (
                <Text c="dimmed">No automated schedules configured.</Text>
              ) : (
                <Table highlightOnHover withTableBorder>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Name</Table.Th>
                      <Table.Th>Type</Table.Th>
                      <Table.Th>Target</Table.Th>
                      <Table.Th>Frequency</Table.Th>
                      <Table.Th>Execution Time</Table.Th>
                      <Table.Th>Repository Path</Table.Th>
                      <Table.Th>Active</Table.Th>
                      <Table.Th>Actions</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {schedules.map((s) => (
                      <Table.Tr key={s.id}>
                        <Table.Td fw={600}>{s.name}</Table.Td>
                        <Table.Td>
                          <Badge color={s.schedule_type === "global" ? "grape" : "blue"}>
                            {s.schedule_type}
                          </Badge>
                        </Table.Td>
                        <Table.Td>{s.target_dataset}</Table.Td>
                        <Table.Td style={{ textTransform: "capitalize" }}>{s.frequency}</Table.Td>
                        <Table.Td>{s.execution_time}</Table.Td>
                        <Table.Td>
                          <Text size="xs" ff="monospace">
                            {s.repository_path}
                          </Text>
                        </Table.Td>
                        <Table.Td>
                          {s.is_active ? (
                            <Badge color="green">Active</Badge>
                          ) : (
                            <Badge color="gray">Inactive</Badge>
                          )}
                        </Table.Td>
                        <Table.Td>
                          <Button
                            size="xs"
                            variant="light"
                            leftSection={<FaPlay size={10} />}
                            loading={runSchedule.isPending}
                            onClick={() => handleRunSchedule(s.id)}
                          >
                            Run Now
                          </Button>
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              )}
            </Card>
          </Tabs.Panel>
        </Tabs>
      </Stack>

      {/* Trigger Backup Modal */}
      <Modal
        opened={triggerModalOpen}
        onClose={() => setTriggerModalOpen(false)}
        title="Trigger Manual Backup"
        size="md"
      >
        <Stack gap="md">
          <Select
            label="Backup Scope"
            description="Local dataset backup (SysAdmin) or Global institute-wide backup (Super Admin only)"
            value={scope}
            onChange={(val) => setScope((val as "local" | "global") || "local")}
            data={[
              { value: "local", label: "Local / Dataset Backup" },
              { value: "global", label: "Global System Backup (Super Admin)" },
            ]}
          />

          <TextInput
            label="Target Dataset"
            description="Dataset identifier, database name, or 'all'"
            value={dataset}
            onChange={(e) => setDataset(e.currentTarget.value)}
            required
          />

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setTriggerModalOpen(false)}>
              Cancel
            </Button>
            <Button loading={triggerBackup.isPending} onClick={handleTrigger}>
              Execute Backup
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
