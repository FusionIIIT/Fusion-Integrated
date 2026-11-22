import { useEffect, useState } from "react";
import {
  Badge,
  Card,
  Container,
  Grid,
  Paper,
  Text,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { PageHeader } from "../../../ui/components/PageHeader";
import { leaveApi } from "../api/client";
import type { LeaveBalance, LeaveLedgerEntry } from "../api/types";

export default function BalancesPage() {
  const [loading, setLoading] = useState(true);
  const [balance, setBalance] = useState<LeaveBalance | null>(null);
  const [ledger, setLedger] = useState<LeaveLedgerEntry[]>([]);

  useEffect(() => {
    const fetchBalances = async () => {
      try {
        setLoading(true);
        const data = await leaveApi.getBalances();
        setBalance(data.balance);
        setLedger(data.ledger);
      } catch (err) {
        notifications.show({
          title: "Error",
          message: errorMessage(err),
          color: "red",
        });
      } finally {
        setLoading(false);
      }
    };
    fetchBalances();
  }, []);

  const balanceCards = balance
    ? [
        { title: "Casual Leave (CL)", val: balance.cl_balance, sub: "Lapses year-end" },
        { title: "Restricted Holiday (RH)", val: balance.rh_balance, sub: "Lapses year-end" },
        { title: "Special Casual Leave (SCL)", val: balance.scl_balance, sub: "Lapses year-end" },
        { title: "Earned Leave (EL)", val: balance.el_balance, sub: "Carries forward" },
        { title: "Vacation Leave (VL)", val: balance.vl_balance, sub: "Converts 2:1 to EL" },
        { title: "Commuted Leave (COL)", val: balance.col_balance, sub: "Carries forward" },
      ]
    : [];

  return (
    <Container size="xl">
      <PageHeader
        title="Leave Balances & History"
        subtitle="Annual entitlements, available balances, and complete ledger adjustments."
      />

      <Grid mb="xl">
        {balanceCards.map((c) => (
          <Grid.Col key={c.title} span={{ base: 12, sm: 4, md: 2 }}>
            <Paper p="md" shadow="xs" radius="md" withBorder>
              <Text size="xs" c="dimmed" fw={600}>{c.title}</Text>
              <Title order={2} my="xs">{c.val}</Title>
              <Text size="xs" c="dimmed">{c.sub}</Text>
            </Paper>
          </Grid.Col>
        ))}
      </Grid>

      <Title order={4} mb="md">Audit Ledger History</Title>
      <Card padding="lg" shadow="sm" radius="md" withBorder>
        <DataTable<LeaveLedgerEntry>
          rows={ledger}
          loading={loading}
          rowKey={(r) => r.id}
          empty={{ title: "No ledger entries", description: "You have no balance adjustments recorded yet." }}
          columns={[
            { key: "created_at", header: "Date", render: (r) => new Date(r.created_at).toLocaleDateString() },
            { key: "category", header: "Category", render: (r) => <Badge variant="light">{r.category}</Badge> },
            {
              key: "entry_type",
              header: "Entry Type",
              render: (r) => <Text size="sm" tt="capitalize">{r.entry_type}</Text>,
            },
            {
              key: "change_amount",
              header: "Change",
              render: (r) => (
                <Text
                  fw={600}
                  c={r.change_amount.startsWith("-") ? "red" : "teal"}
                >
                  {r.change_amount}
                </Text>
              ),
            },
            { key: "balance_after", header: "Balance After", render: (r) => r.balance_after },
            { key: "remarks", header: "Remarks", render: (r) => r.remarks || "—" },
          ]}
        />
      </Card>
    </Container>
  );
}
