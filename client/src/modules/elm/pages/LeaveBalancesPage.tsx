import { Card, Container, SimpleGrid, Text, ThemeIcon, Title } from "@mantine/core";
import { FaChartBar } from "react-icons/fa";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useBalances } from "../api/hooks";
import type { LeaveBalance } from "../api/types";

const DESCRIPTIONS: Record<string, string> = {
  CL: "Casual Leave - for unforeseen personal matters",
  RH: "Restricted Holiday - optional institutional holidays",
  SCL: "Special Casual Leave - academic or official duty",
  EL: "Earned Leave - accumulated leaves for extended rest",
  VL: "Vacation Leave - semester recess leaves",
  COL: "Commuted Leave - medical leave with certificate",
};

export default function LeaveBalancesPage() {
  const { data: balances, isPending, error } = useBalances();

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  return (
    <Container size="xl">
      <PageHeader
        title="Leave Balances"
        subtitle="Current available leave balance breakdown for the academic year"
      />

      {isPending ? (
        <Text c="dimmed">Loading balances...</Text>
      ) : (
        <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="lg">
          {balances?.map((b: LeaveBalance) => (
            <Card key={b.id} padding="lg" withBorder shadow="sm" radius="md">
              <ThemeIcon size={48} radius="md" variant="light" color="blue" mb="md">
                <FaChartBar size={24} />
              </ThemeIcon>
              <Title order={3}>{b.leave_type}</Title>
              <Text size="xl" fw={700} c="blue" my="xs">
                {b.balance} days
              </Text>
              <Text size="sm" c="dimmed">
                {DESCRIPTIONS[b.leave_type] ?? "Leave quota balance"}
              </Text>
            </Card>
          ))}
        </SimpleGrid>
      )}
    </Container>
  );
}

