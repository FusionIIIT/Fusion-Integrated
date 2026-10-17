import { Card, Container, Grid, Stack, Table, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { LeaveApplicationForm } from "../LeaveApplicationForm";
import { useApply, useBalances } from "../api/hooks";
import { CATEGORY_LABELS } from "../api/types";

export default function ApplyLeavePage() {
  const apply = useApply();
  const balances = useBalances();

  return (
    <Container size="xl">
      <PageHeader
        title="Apply for Leave"
        subtitle="Your request goes to your Unit Head first"
      />
      <Grid>
        <Grid.Col span={{ base: 12, md: 8 }}>
          <Card padding="lg">
            <LeaveApplicationForm
              submitting={apply.isPending}
              error={apply.error}
              onSubmit={(body, reset) => apply.mutate(body, {
                onSuccess: (r) => {
                  reset();
                  notifications.show({
                    color: "green", title: "Submitted",
                    message: `${CATEGORY_LABELS[r.category]} for ${r.days} day(s) is pending.`,
                  });
                },
              })}
            />
          </Card>
        </Grid.Col>
        <Grid.Col span={{ base: 12, md: 4 }}>
          <Card padding="lg">
            <Stack gap="xs">
              <Text fw={600}>Balance this year</Text>
              {balances.error ? <ErrorState error={balances.error} /> : (
                <Table>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Category</Table.Th>
                      <Table.Th ta="right">Available</Table.Th>
                      <Table.Th ta="right">Pending</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {(balances.data ?? []).map((b) => (
                      <Table.Tr key={b.category}>
                        <Table.Td>{b.category}</Table.Td>
                        <Table.Td ta="right">{b.available}</Table.Td>
                        <Table.Td ta="right">{b.reserved}</Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              )}
            </Stack>
          </Card>
        </Grid.Col>
      </Grid>
    </Container>
  );
}
