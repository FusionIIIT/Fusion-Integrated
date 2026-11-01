/* eslint-disable react/prop-types */
import { Group, Stack, Text, Title } from "@mantine/core";

const PageHeader = ({ title, subtitle, action }) => (
  <Group justify="space-between" align="flex-end" mb="lg" wrap="wrap">
    <Stack gap={2}>
      <Title order={2}>{title}</Title>
      {subtitle && (
        <Text c="dimmed" size="sm">
          {subtitle}
        </Text>
      )}
    </Stack>
    {action}
  </Group>
);

export default PageHeader;
