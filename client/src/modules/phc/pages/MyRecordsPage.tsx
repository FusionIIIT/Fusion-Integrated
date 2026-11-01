import { Group, Stack, Card, Text, Title, Divider } from "@mantine/core";
import { useMyVisits } from "../api/hooks";
import type { Visit } from "../api/types";
import { PageHeader } from "../../../ui/components/PageHeader";

export function MyRecordsPage() {
  const { data, isLoading } = useMyVisits();

  if (isLoading) return <Text>Loading...</Text>;

  const visits = data?.results || [];

  return (
    <>
      <PageHeader title="My Medical Records" />
      <Stack gap="md">
        {visits.length === 0 ? (
          <Text>No visits recorded yet.</Text>
        ) : (
          visits.map((visit) => (
            <Card key={visit.id} shadow="sm" p="md">
              <Group justify="space-between">
                <Stack gap={2}>
                  <Title order={4}>{new Date(visit.visit_date).toLocaleDateString()}</Title>
                  <Text c="dimmed">{visit.complaint}</Text>
                  {visit.diagnosis && (
                    <>
                      <Divider />
                      <Text fw={500}>Diagnosis: {visit.diagnosis}</Text>
                    </>
                  )}
                </Stack>
              </Group>

              {visit.prescriptions.length > 0 && (
                <Stack gap="xs" mt="md">
                  <Text fw={500}>Prescriptions:</Text>
                  {visit.prescriptions.map((presc) => (
                    <Text key={presc.id} size="sm">
                      • {presc.medicine}, {presc.dosage}mg, every {presc.duration_days} days
                    </Text>
                  ))}
                </Stack>
              )}
            </Card>
          ))
        )}
      </Stack>
    </>
  );
}
