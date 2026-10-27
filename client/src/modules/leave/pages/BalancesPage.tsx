import {
  Badge,
  Card,
  Container,
  Group,
  Progress,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { FaCheckCircle, FaInfoCircle } from "react-icons/fa";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useLeaveBalances } from "../api/hooks";

const CATEGORY_NAMES: Record<string, { label: string; desc: string; carry: boolean }> = {
  CL: {
    label: "Casual Leave (CL)",
    desc: "Short unplanned or personal absences. 8 days annual entitlement; lapses at year-end.",
    carry: false,
  },
  RH: {
    label: "Restricted Holiday (RH)",
    desc: "Selected festive or cultural observances from published list. 2 days max per year.",
    carry: false,
  },
  SCL: {
    label: "Special Casual Leave (SCL)",
    desc: "Academic conferences, examination duties, and official institute obligations.",
    carry: false,
  },
  EL: {
    label: "Earned Leave (EL)",
    desc: "Standard long leave accumulated across active service. Carries forward annually.",
    carry: true,
  },
  COL: {
    label: "Commuted Leave (COL)",
    desc: "Medical leaves supported by certified practitioner reports. Debited at 2x half-pay.",
    carry: true,
  },
  VL: {
    label: "Vacation Leave (VL)",
    desc: "Faculty vacation periods. 50% of unspent balance converts into EL at year-end.",
    carry: false,
  },
};

export default function BalancesPage() {
  const { data: balances, isLoading, error } = useLeaveBalances();

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  return (
    <Container size="xl" py="md">
      <PageHeader
        title="Leave Balances & Entitlements"
        description="Official leave ledger balances for the current calendar year (BR-EL-001..009)."
      />

      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg" mt="lg">
        {(balances || []).map((bal) => {
          const info = CATEGORY_NAMES[bal.category] || {
            label: bal.category,
            desc: "Institute entitlement category",
            carry: false,
          };
          const pctUsed = bal.allocated > 0 ? (bal.used / bal.allocated) * 100 : 0;
          const pctPending =
            bal.allocated > 0 ? (bal.pending / bal.allocated) * 100 : 0;

          return (
            <Card key={bal.id} withBorder radius="md" p="lg">
              <Group justify="space-between" mb="xs">
                <Title order={4}>{info.label}</Title>
                <Badge color={info.carry ? "teal" : "gray"}>
                  {info.carry ? "Carries Forward" : "Lapses Year-End"}
                </Badge>
              </Group>

              <Text size="sm" c="dimmed" mb="md">
                {info.desc}
              </Text>

              <Group justify="space-between" mb="xs">
                <Text size="sm">Available Quota</Text>
                <Text size="lg" fw={700} c="blue">
                  {bal.available} / {bal.allocated} Days
                </Text>
              </Group>

              <Progress.Root size="lg" radius="xl" mb="md">
                <Progress.Section value={pctUsed} color="indigo">
                  <Progress.Label>{bal.used > 0 ? `${bal.used}d used` : ""}</Progress.Label>
                </Progress.Section>
                <Progress.Section value={pctPending} color="yellow">
                  <Progress.Label>{bal.pending > 0 ? `${bal.pending}d pend` : ""}</Progress.Label>
                </Progress.Section>
              </Progress.Root>

              <Group justify="space-between" mt="sm">
                <Stack gap={2}>
                  <Text size="xs" c="dimmed">
                    Credited
                  </Text>
                  <Text size="sm" fw={600}>
                    {bal.allocated} d
                  </Text>
                </Stack>
                <Stack gap={2}>
                  <Text size="xs" c="dimmed">
                    Consumed
                  </Text>
                  <Text size="sm" fw={600} c="red">
                    {bal.used} d
                  </Text>
                </Stack>
                <Stack gap={2}>
                  <Text size="xs" c="dimmed">
                    In Review
                  </Text>
                  <Text size="sm" fw={600} c="yellow">
                    {bal.pending} d
                  </Text>
                </Stack>
                <Stack gap={2}>
                  <Text size="xs" c="dimmed">
                    Net Remaining
                  </Text>
                  <Text size="sm" fw={700} c="green">
                    {bal.available} d
                  </Text>
                </Stack>
              </Group>
            </Card>
          );
        })}
      </SimpleGrid>
    </Container>
  );
}
