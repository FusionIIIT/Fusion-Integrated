import { Badge, Button, Card, Container, Group, Stack, Text } from "@mantine/core";

import { useAuth } from "../../../auth/AuthProvider";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { notifyDone, notifyError } from "../components/notify";
import { useFinalizeNoDues, useNoDues, useRecordNoDuesResult } from "../api/hooks";
import { AUTHORITY_DOMAIN_BY_ROLE } from "../domain";

export default function NoDuesQueuePage() {
  const { data, error, isPending } = useNoDues();
  const { can, session } = useAuth();
  const record = useRecordNoDuesResult();
  const finalize = useFinalizeNoDues();
  const role = session?.active_role ?? null;
  const ownDomain = role ? AUTHORITY_DOMAIN_BY_ROLE[role] : undefined;
  const canFinalize = can("oap.no_dues_case.approve");

  return (
    <Container size="md" py="md">
      <PageHeader title="No-dues queue" subtitle="Record your domain's result, and finalize once all seven are clear." />
      {error ? <ErrorState error={error} /> : isPending ? null : !data?.length ? (
        <Text c="dimmed">No clearance cases are open.</Text>
      ) : (
        <Stack>
          {data.map((c) => (
            <Card withBorder key={c.id}>
              <Group justify="space-between" mb="xs">
                <Text fw={600}>Clearance #{c.id}</Text>
                <StatusBadge status={c.finalized ? "finalized" : c.status} />
              </Group>
              <Group gap="xs" mb="sm">
                {Object.entries(c.results).map(([domain, result]) => (
                  <Badge key={domain} variant="light" color={result === "clear" ? "green" : result === "outstanding" ? "red" : "gray"}>
                    {domain.replace(/_/g, " ")}: {result}
                  </Badge>
                ))}
              </Group>
              <Group gap="xs">
                {ownDomain && !c.finalized && (
                  <>
                    <Button size="xs" onClick={() => record.mutate({ id: c.id, result: "clear" }, {
                      onSuccess: () => notifyDone("Result recorded."), onError: notifyError })}>Mark clear</Button>
                    <Button size="xs" color="red" variant="light" onClick={() => record.mutate({ id: c.id, result: "outstanding" }, {
                      onSuccess: () => notifyDone("Result recorded."), onError: notifyError })}>Mark outstanding</Button>
                  </>
                )}
                {canFinalize && !c.finalized && (
                  <Button size="xs" variant="filled" onClick={() => finalize.mutate(c.id, {
                    onSuccess: () => notifyDone("Clearance finalized."), onError: notifyError })}>Finalize</Button>
                )}
              </Group>
            </Card>
          ))}
        </Stack>
      )}
    </Container>
  );
}
