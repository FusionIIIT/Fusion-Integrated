import {
  Badge, Button, Card, Container, Group, Stack, Text,
} from "@mantine/core";
import { useNavigate } from "react-router-dom";
import { FaBullhorn, FaPlus } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAdvisories } from "../api/hooks";

export default function AdvisoriesPage() {
  const { data, isPending, error } = useAdvisories();
  const { can } = useAuth();
  const navigate = useNavigate();
  const canPublish = can("phc.advisory.publish");

  if (error) return <Container size="md"><ErrorState error={error} /></Container>;

  const rows = data?.results ?? [];

  return (
    <Container size="md">
      <PageHeader
        title="Health Advisories"
        subtitle="Notices published by the Primary Health Care office"
        action={canPublish && (
          <Button
            leftSection={<FaPlus size={12} />} size="xs"
            onClick={() => navigate("/phc/staff/advisories")}
          >
            Publish
          </Button>
        )}
      />

      {isPending && <Text c="dimmed">Loading…</Text>}

      {!isPending && rows.length === 0 && (
        <Card padding="xl">
          <Stack align="center" gap={6}>
            <FaBullhorn size={24} color="var(--mantine-color-gray-5)" />
            <Text fw={600}>No advisories published</Text>
            <Text size="sm" c="dimmed">
              Health notices from the PHC office will appear here.
            </Text>
          </Stack>
        </Card>
      )}

      <Stack gap="md">
        {rows.map((a) => (
          <Card key={a.id} padding="lg" withBorder>
            <Group justify="space-between" align="flex-start" wrap="nowrap">
              <Stack gap={4} style={{ flex: 1 }}>
                <Group gap="xs">
                  <Text fw={700}>{a.title}</Text>
                  <Badge variant="light" color="teal" size="sm">published</Badge>
                </Group>
                <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                  {a.content}
                </Text>
                <Text size="xs" c="dimmed">
                  {a.published_at
                    ? new Date(a.published_at).toLocaleString() : "unpublished"}
                  {a.published_by ? ` · by user ${a.published_by}` : ""}
                </Text>
              </Stack>
            </Group>
          </Card>
        ))}
      </Stack>
    </Container>
  );
}
