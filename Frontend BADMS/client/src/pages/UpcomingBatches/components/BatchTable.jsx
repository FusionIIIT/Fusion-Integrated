/* eslint-disable react/prop-types */
import { ActionIcon, Badge, Center, Group, Progress, Stack, Table, Text, ThemeIcon, Tooltip } from "@mantine/core";
import { FaEye, FaLayerGroup, FaTrash } from "react-icons/fa";

const BatchTable = ({ batches, onView, onDelete }) => {
  if (!batches.length) {
    return (
      <Center py={48}>
        <Stack gap={8} align="center">
          <ThemeIcon size={54} radius="xl" variant="light" color="gray">
            <FaLayerGroup size={22} />
          </ThemeIcon>
          <Text fw={600}>No batches for this category</Text>
          <Text size="sm" c="dimmed">
            Use the “Add Batch” button to create one and start admitting students.
          </Text>
        </Stack>
      </Center>
    );
  }

  return (
    <Table.ScrollContainer minWidth={760}>
      <Table highlightOnHover verticalSpacing="md" horizontalSpacing="md">
        <Table.Thead style={{ background: "var(--mantine-color-gray-0)" }}>
          <Table.Tr>
            <Table.Th>Batch</Table.Th>
            <Table.Th>Discipline</Table.Th>
            <Table.Th>Year</Table.Th>
            <Table.Th>Curriculum</Table.Th>
            <Table.Th miw={180}>Seats</Table.Th>
            <Table.Th ta="right">Actions</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {batches.map((batch) => {
            const total = batch.total_seats || 0;
            const filled = batch.filled_seats || 0;
            const pct = total ? Math.min(100, Math.round((filled / total) * 100)) : 0;
            return (
              <Table.Tr key={batch.batch_id}>
                <Table.Td>
                  <Text fw={600}>{batch.name}</Text>
                </Table.Td>
                <Table.Td>
                  <Badge variant="light" color="indigo" radius="sm">
                    {batch.discipline}
                  </Badge>
                </Table.Td>
                <Table.Td>{batch.year}</Table.Td>
                <Table.Td>
                  <Text size="sm" c="dimmed" lineClamp={1} maw={220}>
                    {batch.curriculum || "—"}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Stack gap={4} miw={160}>
                    <Group justify="space-between" gap="xs">
                      <Text size="xs" fw={600}>
                        {filled} / {total}
                      </Text>
                      <Text size="xs" c={batch.available_seats > 0 ? "green" : "red"} fw={500}>
                        {batch.available_seats} left
                      </Text>
                    </Group>
                    <Progress value={pct} size="sm" radius="xl" color={batch.available_seats > 0 ? "blue" : "red"} />
                  </Stack>
                </Table.Td>
                <Table.Td>
                  <Group gap={6} justify="flex-end" wrap="nowrap">
                    <Tooltip label="View students" withArrow>
                      <ActionIcon variant="light" size="lg" onClick={() => onView(batch)}>
                        <FaEye size={14} />
                      </ActionIcon>
                    </Tooltip>
                    <Tooltip label="Delete batch" withArrow>
                      <ActionIcon variant="light" color="red" size="lg" onClick={() => onDelete(batch)}>
                        <FaTrash size={13} />
                      </ActionIcon>
                    </Tooltip>
                  </Group>
                </Table.Td>
              </Table.Tr>
            );
          })}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  );
};

export default BatchTable;
