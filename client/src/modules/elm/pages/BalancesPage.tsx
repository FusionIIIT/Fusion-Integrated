import { Card, Container } from "@mantine/core";
import { FaBalanceScale } from "react-icons/fa";

import { useBalances } from "../api/hooks";
import { CATEGORY_LABELS, type LeaveBalance } from "../api/types";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";

export default function BalancesPage() {
  const { data, isPending, error } = useBalances();

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  return (
    <Container size="xl">
      <PageHeader
        title="Leave Balances"
        subtitle="Your current entitlement and what is still available"
      />
      <Card padding="lg">
        <DataTable<LeaveBalance>
          rows={data?.results ?? []}
          loading={isPending}
          rowKey={(r) => r.category}
          columns={[
            { key: "category", header: "Category",
              render: (r) => CATEGORY_LABELS[r.category] ?? r.category },
            { key: "entitled", header: "Entitled", render: (r) => r.entitled },
            { key: "used", header: "Used", render: (r) => r.used },
            { key: "available", header: "Available", render: (r) => r.available },
          ]}
          empty={{
            icon: FaBalanceScale,
            title: "No balances yet",
            description: "Your entitlement appears once you file for leave.",
          }}
        />
      </Card>
    </Container>
  );
}
