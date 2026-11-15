import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCatalogue, useCreateApplication } from "../api/hooks";

function showDate(value: string | null): string {
  return value ?? "Not specified";
}

export default function CataloguePage() {
  const catalogue = useCatalogue();
  const createApplication = useCreateApplication();
  const [academicCycle, setAcademicCycle] = useState("");

  function startApplication(catalogueVersionId: number) {
    const cycle = academicCycle.trim();
    if (!cycle) {
      notifications.show({
        color: "red",
        title: "Academic cycle required",
        message: "Enter the academic cycle before starting an application.",
      });
      return;
    }

    createApplication.mutate(
      { catalogue_version_id: catalogueVersionId, academic_cycle: cycle },
      {
        onSuccess: () => notifications.show({
          color: "green",
          title: "Draft created",
          message: "Your application draft is ready to edit.",
        }),
        onError: (error) => notifications.show({
          color: "red",
          title: "Could not start application",
          message: errorMessage(error),
        }),
      },
    );
  }

  if (catalogue.error) {
    return <Container size="xl"><ErrorState error={catalogue.error} /></Container>;
  }

  return (
    <Container size="xl">
      <PageHeader
        title="Scholarships and Awards"
        subtitle="Published catalogue versions and their configured details"
      />
      <Stack gap="lg">
        <TextInput
          label="Academic cycle"
          placeholder="Enter the academic cycle"
          value={academicCycle}
          onChange={(event) => setAcademicCycle(event.currentTarget.value)}
          required
        />
        {catalogue.isPending && <Text c="dimmed">Loading catalogue…</Text>}
        {!catalogue.isPending && catalogue.data?.length === 0 && (
          <Text c="dimmed">No published catalogue versions are available.</Text>
        )}
        <SimpleGrid cols={{ base: 1, md: 2 }}>
          {(catalogue.data ?? []).map((version) => (
            <Card key={version.id} withBorder padding="lg">
              <Stack gap="sm">
                <Group justify="space-between">
                  <Text fw={700}>
                    {version.entry_kind} {version.entry_id}
                  </Text>
                  <Badge>{version.status}</Badge>
                </Group>
                <Text size="sm">Version {version.version_number}</Text>
                <Text size="sm">
                  Effective: {showDate(version.effective_from)} –{" "}
                  {showDate(version.effective_to)}
                </Text>
                <Text size="sm">
                  Application window: {showDate(version.application_opens_at)} –{" "}
                  {showDate(version.application_closes_at)}
                </Text>
                <Text fw={600} size="sm">Configured details</Text>
                <pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>
                  {JSON.stringify(version.configuration, null, 2)}
                </pre>
                {version.entry_kind === "scholarship" && (
                  <Button
                    onClick={() => startApplication(version.id)}
                    loading={createApplication.isPending}
                  >
                    Start application
                  </Button>
                )}
              </Stack>
            </Card>
          ))}
        </SimpleGrid>
      </Stack>
    </Container>
  );
}
