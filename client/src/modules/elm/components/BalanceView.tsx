import { Card, SimpleGrid, Stack, Text } from "@mantine/core";

import { DataTable } from "../../../ui/components/DataTable";
import { CATEGORY_LABELS, type Balance, type Category } from "../api/types";

export function BalanceView({ data, loading }: { data?: Balance; loading: boolean }) {
  const cats = Object.keys(CATEGORY_LABELS) as Category[];
  return (
    <Stack gap="lg">
      <SimpleGrid cols={{ base: 2, sm: 3, md: 6 }}>
        {cats.map((c) => (
          <Card key={c} withBorder padding="md">
            <Text size="xs" c="dimmed">{CATEGORY_LABELS[c]}</Text>
            <Text fw={700} size="xl">{data ? Number(data.balances[c]) : "—"}</Text>
            {data && Number(data.pending[c]) > 0 && (
              <Text size="xs" c="orange">{Number(data.pending[c])} pending</Text>
            )}
          </Card>
        ))}
      </SimpleGrid>
      <Card withBorder padding="md">
        <Text fw={600} mb="sm">Leave-account history</Text>
        <DataTable
          rows={data?.history ?? []} loading={loading} rowKey={(r) => r.id}
          empty={{ title: "No entries yet",
            description: "Credits and debits appear here as they are posted." }}
          columns={[
            { key: "at", header: "When", render: (r) => new Date(r.at).toLocaleDateString() },
            { key: "category", header: "Leave", render: (r) => r.category },
            { key: "type", header: "Entry", render: (r) => r.entry_type.replace(/_/g, " ") },
            { key: "delta", header: "Days", align: "right",
              render: (r) => (
                <Text size="sm" c={Number(r.delta) < 0 ? "red" : "green"}>{r.delta}</Text>) },
            { key: "note", header: "Note", render: (r) => r.note },
          ]}
        />
      </Card>
    </Stack>
  );
}
