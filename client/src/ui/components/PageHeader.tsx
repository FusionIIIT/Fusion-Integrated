import { Group, Stack, Text, Title } from "@mantine/core";

/** Ported from the sysadmin client. Page identity is carried by this, not by
 *  breadcrumbs — that app has none, and neither does this one. */
export function PageHeader({ title, subtitle, action }: {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
}) {
  return (
    <Group justify="space-between" align="flex-end" mb="lg" wrap="wrap">
      <Stack gap={2}>
        <Title order={2}>{title}</Title>
        {subtitle && <Text c="dimmed" size="sm">{subtitle}</Text>}
      </Stack>
      {action}
    </Group>
  );
}
