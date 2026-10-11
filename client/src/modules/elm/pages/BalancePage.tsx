import { useState } from "react";
import { Card, Container, NumberInput, Text } from "@mantine/core";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useBalances } from "../api/hooks";
import type { Balance } from "../api/types";

export default function BalancePage() {
  const [year, setYear] = useState(new Date().getFullYear());
  const { data, isPending, error } = useBalances(undefined, year);

  if (error) {
    return <Container size="lg"><ErrorState error={error} /></Container>;
  }

  return (
    <Container size="lg">
      <PageHeader
        title="My Balances"
        subtitle="Entitled, used and available days per leave type"
        action={
          <NumberInput
            label="Year" value={year} min={2000} max={2100} w={120}
            onChange={(value) => setYear(Number(value) || new Date().getFullYear())}
          />
        }
      />
      <Card padding="lg">
        <DataTable<Balance>
          rows={(data ?? []) as Balance[]}
          loading={isPending}
          rowKey={(r) => r.leave_type_code}
          minWidth={560}
          empty={{
            title: "No balances for this year",
            description: "A balance appears once a leave type is effective.",
          }}
          columns={[
            {
              key: "type", header: "Leave type",
              render: (r) => (
                <Text fw={600}>{r.leave_type_code} — {r.leave_type_name}</Text>
              ),
            },
            { key: "entitled", header: "Entitled", render: (r) => r.entitled_days },
            { key: "used", header: "Used", render: (r) => r.used_days },
            {
              key: "available", header: "Available",
              render: (r) => <Text fw={600}>{r.available_days}</Text>,
            },
          ]}
        />
      </Card>
    </Container>
  );
}
