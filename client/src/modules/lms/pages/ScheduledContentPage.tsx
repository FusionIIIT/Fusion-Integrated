import React from "react";
import { useNavigate } from "react-router-dom";
import {
  Alert,
  Badge,
  Button,
  Card,
  Group,
  Loader,
  Paper,
  Stack,
  Table,
  Text,
  Title,
} from "@mantine/core";
import { useScheduledReleases } from "../api/hooks";
import type { ScheduledRelease } from "../api/types";

export const ScheduledContentPage: React.FC = () => {
  const navigate = useNavigate();
  const { data: scheduledReleases = [], isLoading, error } = useScheduledReleases();

  const getStatusBadge = (release: ScheduledRelease) => {
    if (release.is_cancelled) {
      return <Badge color="red" variant="filled">Cancelled</Badge>;
    }
    if (release.processed_at) {
      return <Badge color="green" variant="filled">Published</Badge>;
    }
    return <Badge color="blue" variant="light">Pending Schedule</Badge>;
  };

  return (
    <Stack gap="lg" p="md">
      <Group justify="space-between">
        <div>
          <Title order={2}>Scheduled Content Releases</Title>
          <Text c="dimmed">
            Automated publication queue for course materials and assignments
          </Text>
        </div>
        <Button variant="default" onClick={() => navigate("/courses")}>
          Courses Dashboard
        </Button>
      </Group>

      <Alert color="blue" title="Automated Content Scheduling Engine">
        Items in this registry are periodically scanned and automatically published by the background
        scheduler upon reaching their designated target timestamp.
      </Alert>

      {isLoading ? (
        <Group justify="center" p="xl">
          <Loader size="md" />
          <Text c="dimmed">Loading scheduled releases...</Text>
        </Group>
      ) : error ? (
        <Alert color="red" title="Error Loading Schedule">
          Failed to load scheduled releases. Please try again.
        </Alert>
      ) : scheduledReleases.length === 0 ? (
        <Paper withBorder p="xl" style={{ textAlign: "center" }}>
          <Text c="dimmed">No scheduled releases found in the queue.</Text>
        </Paper>
      ) : (
        <Card withBorder padding="none">
          <Table striped highlightOnHover verticalSpacing="sm" horizontalSpacing="md">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>ID</Table.Th>
                <Table.Th>Target Type</Table.Th>
                <Table.Th>Target Reference</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Scheduled Publication</Table.Th>
                <Table.Th>Published Timestamp</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {scheduledReleases.map((release) => {
                const targetType = release.assignment ? "Assignment" : "Material";
                const targetRef = release.assignment
                  ? `Assignment #${release.assignment}`
                  : release.material
                  ? `Material #${release.material}`
                  : "Unspecified";

                return (
                  <Table.Tr key={release.id}>
                    <Table.Td>
                      <Text size="sm" fw={600}>#{release.id}</Text>
                    </Table.Td>
                    <Table.Td>
                      <Badge
                        variant="outline"
                        color={release.assignment ? "orange" : "teal"}
                      >
                        {targetType}
                      </Badge>
                    </Table.Td>
                    <Table.Td>
                      <Text fw={600}>{targetRef}</Text>
                    </Table.Td>
                    <Table.Td>{getStatusBadge(release)}</Table.Td>
                    <Table.Td>
                      <Text size="sm">
                        {new Date(release.scheduled_publish_at).toLocaleString()}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm" c={release.processed_at ? "dark" : "dimmed"}>
                        {release.processed_at
                          ? new Date(release.processed_at).toLocaleString()
                          : "Pending"}
                      </Text>
                    </Table.Td>
                  </Table.Tr>
                );
              })}
            </Table.Tbody>
          </Table>
        </Card>
      )}
    </Stack>
  );
};

export default ScheduledContentPage;
