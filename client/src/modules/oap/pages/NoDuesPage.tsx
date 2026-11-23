import { Badge, Button, Card, Container, Group, Stack, Text } from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { notifyDone, notifyError } from "../components/notify";
import { useInitiateNoDues, useNoDues } from "../api/hooks";

export default function NoDuesPage() {
  const { data, error, isPending } = useNoDues();
  const initiate = useInitiateNoDues();

  return (
    <Container size="md" py="md">
      <PageHeader
        title="No-dues clearance"
        subtitle="Start clearance and follow each authority's result."
        action={
          <Button loading={initiate.isPending} onClick={() => initiate.mutate(undefined, {
            onSuccess: () => notifyDone("No-dues clearance started."), onError: notifyError,
          })}>Start clearance</Button>
        }
      />
      {error ? <ErrorState error={error} /> : isPending ? null : !data?.length ? (
        <Text c="dimmed">No clearance cases yet.</Text>
      ) : (
        <Stack>
          {data.map((c) => (
            <Card withBorder key={c.id}>
              <Group justify="space-between" mb="xs">
                <Text fw={600}>Clearance #{c.id}</Text>
                <StatusBadge status={c.finalized ? "finalized" : c.status} />
              </Group>
              <Group gap="xs">
                {Object.entries(c.results).map(([domain, result]) => (
                  <Badge key={domain} variant="light" color={result === "clear" ? "green" : result === "outstanding" ? "red" : "gray"}>
                    {domain.replace(/_/g, " ")}: {result}
                  </Badge>
                ))}
              </Group>
              {c.finalized && <Text size="sm" mt="xs">Your no-dues certificate is ready.</Text>}
            </Card>
          ))}
        </Stack>
      )}
    </Container>
  );
}
