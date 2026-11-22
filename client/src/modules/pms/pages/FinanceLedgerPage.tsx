import {
  Card,
  Container,
  Table,
  Text,
  Title,
} from "@mantine/core";
import { FaReceipt } from "react-icons/fa";

import { PageHeader } from "../../../ui/components/PageHeader";

export default function FinanceLedgerPage() {
  return (
    <Container size="xl" py="md">
      <PageHeader
        title="Patent Financial Ledger"
        subtitle="Immutable append-only audit ledger of patent filing, legal, examination, and maintenance expenses."
        icon={<FaReceipt size={28} />}
      />

      <Card shadow="xs" padding="lg" radius="md" withBorder mt="md">
        <Title order={4} mb="md">
          Institution-Wide Patent Financial Transactions
        </Title>
        <Text size="sm" c="dimmed">
          All financial disbursements adhere to §2.7: Balances are computed dynamically from immutable ledger entries.
        </Text>
      </Card>
    </Container>
  );
}
