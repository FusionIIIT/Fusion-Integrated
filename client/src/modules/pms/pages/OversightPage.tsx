import { Card, Container, SimpleGrid, Text } from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useOversight } from "../api/hooks";
import { words } from "../components/format";
import { ApplicationsTable } from "../components/Lists";

// UC-PMS-032: workflow state within the caller's own areas or the whole office.
export default function OversightPage() {
  const data = useOversight();
  return (
    <Container size="xl" pt="md">
      <PageHeader title="Oversight" subtitle="Where every application in your scope stands" />
      {data.error ? <ErrorState error={data.error} /> : (
        <SimpleGrid cols={{ base: 2, md: 4 }} mb="lg">
          <Card withBorder><Text size="xs" c="dimmed">Applications</Text>
            <Text fw={700} size="xl">{data.isPending ? "…" : data.data.total}</Text></Card>
          <Card withBorder><Text size="xs" c="dimmed">Overdue reviews</Text>
            <Text fw={700} size="xl">{data.isPending ? "…" : data.data.overdue_reviews}</Text></Card>
          <Card withBorder><Text size="xs" c="dimmed">Open escalations</Text>
            <Text fw={700} size="xl">{data.isPending ? "…" : data.data.open_escalations}</Text></Card>
          {!data.isPending && Object.entries(data.data.by_status).filter(([, n]) => n > 0)
            .map(([s, n]) => (
              <Card key={s} withBorder><Text size="xs" c="dimmed">{words(s)}</Text>
                <Text fw={700} size="xl">{n}</Text></Card>
            ))}
        </SimpleGrid>
      )}
      <ApplicationsTable emptyTitle="No applications in your scope" />
    </Container>
  );
}
