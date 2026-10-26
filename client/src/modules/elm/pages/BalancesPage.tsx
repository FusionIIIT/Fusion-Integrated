import { useQuery } from "@tanstack/react-query";
import { Alert, Card, Container, Grid, Loader, SimpleGrid, Stack, Text } from "@mantine/core";

import { errorMessage, http } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";

type Balance = {
  leave_type_code: string;
  year: number;
  annual_entitlement: string | null;
  opening_balance: string;
  annual_credit: string;
  used_days: string;
  reserved_days: string;
  available_days: string;
  carries_forward: boolean;
};

export default function BalancesPage() {
  const query = useQuery({
    queryKey: ["elm", "balances"],
    queryFn: async () => (await http.get<{ results: Balance[] }>("/leave/balances")).data.results,
  });

  return (
    <Container size="xl">
      <PageHeader title="Leave balances" subtitle="Your current annual entitlement and available leave" />
      {query.isPending && <Loader />}
      {query.error && <Alert color="red" title="Could not load balances">{errorMessage(query.error)}</Alert>}
      {query.data && (
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }}>
          {query.data.map((balance) => (
            <Card key={balance.leave_type_code} withBorder>
              <Stack gap="xs">
                <Text fw={700}>{balance.leave_type_code} · {balance.year}</Text>
                <Grid>
                  <Grid.Col span={6}><Text size="sm" c="dimmed">Entitlement</Text><Text>{balance.annual_entitlement ?? "Policy controlled"}</Text></Grid.Col>
                  <Grid.Col span={6}><Text size="sm" c="dimmed">Available</Text><Text fw={700}>{balance.available_days}</Text></Grid.Col>
                  <Grid.Col span={6}><Text size="sm" c="dimmed">Used</Text><Text>{balance.used_days}</Text></Grid.Col>
                  <Grid.Col span={6}><Text size="sm" c="dimmed">Pending</Text><Text>{balance.reserved_days}</Text></Grid.Col>
                </Grid>
                <Text size="xs" c="dimmed">{balance.carries_forward ? "Carries forward under policy" : "Unused balance lapses under policy"}</Text>
              </Stack>
            </Card>
          ))}
        </SimpleGrid>
      )}
    </Container>
  );
}
