import { Card, Container, Stack, Text } from "@mantine/core";
import { useState } from "react";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAccount } from "../api/hooks";
import { BalanceView } from "../components/BalanceView";
import { EmployeePicker } from "../components/EmployeePicker";

export default function AccountsPage() {
  const [uid, setUid] = useState<number | null>(null);
  const { data, isFetching, error } = useAccount(uid);
  return (
    <Container size="xl">
      <PageHeader title="Leave Accounts" subtitle="Any employee's balances and history" />
      <Card withBorder padding="md" mb="lg">
        <EmployeePicker label="Employee" value={uid} onChange={setUid} />
      </Card>
      {error && <ErrorState error={error} />}
      {uid == null ? (
        <Text c="dimmed" size="sm">Choose an employee to see their leave account.</Text>
      ) : (
        <Stack>
          {data?.display_name && <Text fw={600}>{data.display_name}</Text>}
          <BalanceView data={data} loading={isFetching} />
        </Stack>
      )}
    </Container>
  );
}
