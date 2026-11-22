import { useState } from "react";
import { Badge, Button, Card, Container, Group, SimpleGrid, Stack, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { Link } from "react-router-dom";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useBackupRuns, useRunManualBackup } from "../api/hooks";

export default function OverviewPage() {
  const { can } = useAuth();
  const { data, isPending } = useBackupRuns();
  const run = useRunManualBackup();
  const [starting, setStarting] = useState(false);
  const runs = data?.results ?? [];

  async function startBackup() {
    setStarting(true);
    try {
      await run.mutateAsync();
      notifications.show({ title: "Backup queued", message: "The run will appear in history." });
    } catch (error) {
      notifications.show({ title: "Could not start backup", message: errorMessage(error),
        color: "red" });
    } finally {
      setStarting(false);
    }
  }

  return (
    <Container size="lg">
      <PageHeader title="Backup and Archive Management"
        subtitle="Institutional backups, secure archives, and data recovery" />
      <SimpleGrid cols={{ base: 1, sm: 2 }}>
        <Card withBorder padding="lg">
          <Stack>
            <Text fw={700}>Backup history</Text>
            <Text c="dimmed" size="sm">
              {isPending ? "Loading backup status…" : `${runs.length} recent runs`}
            </Text>
            {can("badms.backup.run_manual") && (
              <Button loading={starting} onClick={startBackup}>Run backup now</Button>
            )}
          </Stack>
        </Card>
        <Card withBorder padding="lg">
          <Stack>
            <Text fw={700}>Secure archives</Text>
            <Text c="dimmed" size="sm">Submit a file or review a request you can access.</Text>
            <Button component={Link} to="archives" variant="light">Open archives</Button>
          </Stack>
        </Card>
      </SimpleGrid>
      <Stack mt="lg" gap="sm">
        {runs.map((item) => (
          <Card key={item.id} withBorder padding="md">
            <Group justify="space-between">
              <Stack gap={2}>
                <Text fw={600}>Run #{item.id} · {item.dataset}</Text>
                <Text size="sm" c="dimmed">{new Date(item.started_at).toLocaleString()}</Text>
              </Stack>
              <Badge color={item.status === "success" ? "green" :
                item.status === "failure" ? "red" : "blue"}>{item.status}</Badge>
            </Group>
          </Card>
        ))}
      </Stack>
    </Container>
  );
}
