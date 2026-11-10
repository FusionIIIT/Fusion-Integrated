import { Stack, Text, Title } from "@mantine/core";

interface VmsPageProps {
  title: string;
  description: string;
  /** API endpoints (under /api/v1/vms/) this screen will call. */
  endpoints: string[];
}

/** Placeholder shell for a Visitor Management screen until its UI lands. */
export default function VmsPage({ title, description, endpoints }: VmsPageProps) {
  return (
    <Stack gap="xs">
      <Title order={2}>{title}</Title>
      <Text>{description}</Text>
      <Text size="sm" c="dimmed">
        Will use: {endpoints.join(", ")}
      </Text>
    </Stack>
  );
}
