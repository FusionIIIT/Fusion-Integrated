import { Container } from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useBalances } from "../api/hooks";
import { BalanceView } from "../components/BalanceView";

export default function BalancesPage() {
  const { data, isPending, error } = useBalances();
  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;
  return (
    <Container size="xl">
      <PageHeader title="Balances & History"
        subtitle="Current balances, pending reservations and every posted entry" />
      <BalanceView data={data} loading={isPending} />
    </Container>
  );
}
