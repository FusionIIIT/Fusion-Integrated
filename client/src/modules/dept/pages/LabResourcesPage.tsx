import { Alert, Badge, Card, Container, Group, SimpleGrid, Stack, Text, Title } from "@mantine/core";

import { useLabResources } from "../api/hooks";

export default function LabResourcesPage() {
  const { data: labs, isLoading } = useLabResources();

  return (
    <Container size="lg" py="xl">
      <Group justify="space-between" mb="lg">
        <div>
          <Title order={2}>Department Laboratories</Title>
          <Text c="dimmed">Lab infrastructure, facilities, and equipment inventory</Text>
        </div>
      </Group>

      {isLoading && <Text>Loading labs...</Text>}

      {labs && labs.length === 0 && (
        <Alert title="No Laboratories" color="blue">
          No lab resources are currently registered in this department.
        </Alert>
      )}

      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg">
        {labs?.map((lab) => (
          <Card key={lab.id} withBorder shadow="sm" radius="md">
            <Group justify="space-between" mb="xs">
              <Title order={4}>{lab.lab_name}</Title>
              <Badge color="blue">{lab.location}</Badge>
            </Group>
            <Text size="sm" c="dimmed" mb="md">{lab.description || "No description provided."}</Text>
            <Text size="sm"><b>Faculty In-Charge:</b> {lab.in_charge_id || "Unassigned"}</Text>
            {lab.equipment_details && lab.equipment_details.length > 0 && (
              <Stack gap="xs" mt="sm">
                <Text size="xs" fw={700} c="dimmed">EQUIPMENT LIST:</Text>
                {lab.equipment_details.map((eq, idx) => (
                  <Badge key={idx} variant="outline" color="gray">
                    {typeof eq === "object" && eq !== null ? JSON.stringify(eq) : String(eq)}
                  </Badge>
                ))}
              </Stack>
            )}
          </Card>
        ))}
      </SimpleGrid>
    </Container>
  );
}
