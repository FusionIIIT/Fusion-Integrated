import { useState } from "react";
import {
  Card, Container, Group, NumberInput, SimpleGrid, Stack, Table, Text,
} from "@mantine/core";
import { FaBalanceScale } from "react-icons/fa";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { formatDay } from "../components/PeriodCell";
import { useBalanceDirectory, useMyBalances, useStatement } from "../api/hooks";
import type { Balance, LedgerEntry } from "../api/types";

/** Two things on one screen: the totals, and the entries that produced them.
 *  A figure nobody can explain is a figure that gets disputed, so the rows are
 *  one click away rather than a support request away. */
export default function BalancesPage() {
  const [userId, setUserId] = useState<number | "">("");
  const [category, setCategory] = useState<string | null>(null);

  const mine = useMyBalances();
  const directory = useBalanceDirectory(userId === "" ? null : Number(userId));
  const statement = useStatement(category);

  const showing: Balance[] = (userId === "" ? mine.data : directory.data) ?? [];
  const error = userId === "" ? mine.error : directory.error;

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  return (
    <Container size="xl">
      <PageHeader
        title="Balances"
        subtitle="Derived from the leave account, entry by entry"
        action={
          <NumberInput
            placeholder="Employee ID" w={180} value={userId} min={1}
            allowDecimal={false}
            onChange={(v) => { setUserId(v === "" ? "" : Number(v)); setCategory(null); }}
          />
        }
      />

      <SimpleGrid cols={{ base: 2, sm: 3, lg: 6 }} mb="lg">
        {showing.map((b) => (
          <Card
            key={b.category} padding="md" withBorder
            style={{ cursor: userId === "" ? "pointer" : "default" }}
            onClick={() => userId === "" && setCategory(b.category)}
          >
            <Text size="xs" c="dimmed" tt="uppercase" fw={600}>{b.category}</Text>
            <Text fw={700} size="xl">{b.available}</Text>
            <Stack gap={0} mt={4}>
              <Text size="xs" c="dimmed">credited {b.credited}</Text>
              <Text size="xs" c="dimmed">used {b.consumed}</Text>
              <Text size="xs" c="dimmed">restored {b.restored}</Text>
            </Stack>
          </Card>
        ))}
      </SimpleGrid>

      {userId === "" && (
        <Card padding="lg">
          <Group justify="space-between" mb="md">
            <Text fw={600}>
              {category ? `${category} account` : "Select a category above"}
            </Text>
          </Group>
          {category && (
            <DataTable<LedgerEntry>
              rows={statement.data ?? []} loading={statement.isPending}
              rowKey={(r) => r.id} minWidth={760}
              columns={[
                { key: "created_at", header: "Recorded",
                  render: (r) => formatDay(r.created_at.slice(0, 10)) },
                { key: "reason", header: "Reason",
                  render: (r) => r.reason.toLowerCase().replace(/_/g, " ") },
                { key: "days", header: "Days", align: "right",
                  render: (r) => (
                    <Text c={Number(r.days) < 0 ? "red" : "teal"} fw={600}>
                      {Number(r.days) > 0 ? `+${r.days}` : r.days}
                    </Text>
                  ) },
                { key: "note", header: "Note", render: (r) => r.note },
              ]}
              empty={{
                icon: FaBalanceScale,
                title: "No entries in this account",
                description: "Credits and charges appear here as they are made.",
              }}
            />
          )}
        </Card>
      )}

      {userId !== "" && !showing.length && (
        <Card padding="lg">
          <Table.ScrollContainer minWidth={0}>
            <Text c="dimmed" size="sm">
              No leave account exists for employee {userId} yet.
            </Text>
          </Table.ScrollContainer>
        </Card>
      )}
    </Container>
  );
}
