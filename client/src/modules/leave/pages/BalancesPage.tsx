import { Card, Container, SimpleGrid, Text } from "@mantine/core";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useBalances } from "../api/hooks";

export default function BalancesPage() {
  const { data, error, isPending } = useBalances();
  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;
  const bals = data?.balances ?? {};
  return (
    <Container size="xl">
      <PageHeader title="Leave balances" subtitle={`Calendar year ${data?.year ?? ""}`} />
      <SimpleGrid cols={{ base: 2, md: 3 }} mb="lg">
        {Object.entries(bals).map(([cat, val]) => (
          <Card key={cat} padding="md">
            <Text size="xs" c="dimmed">{cat}</Text>
            <Text fw={700} size="xl">{val}</Text>
          </Card>
        ))}
      </SimpleGrid>
      <Card padding="lg">
        <DataTable
          rows={data?.history ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          columns={[
            { key: "created_at", header: "When", render: (r) => r.created_at },
            { key: "category", header: "Category", render: (r) => r.category },
            { key: "entry_type", header: "Type", render: (r) => r.entry_type },
            { key: "amount", header: "Amount", render: (r) => r.amount },
            { key: "memo", header: "Memo", render: (r) => r.memo },
          ]}
        />
      </Card>
    </Container>
  );
}
