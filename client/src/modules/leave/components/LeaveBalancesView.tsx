import {
  Alert,
  Card,
  Center,
  Grid,
  Group,
  Loader,
  Progress,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { FaInfoCircle, FaWallet } from "react-icons/fa";

import { useBalances } from "../api/hooks";
import type { LeaveCategory } from "../api/types";

const CATEGORY_NAMES: Record<LeaveCategory, string> = {
  CL: "Casual Leave",
  RH: "Restricted Holiday",
  SCL: "Special Casual Leave",
  EL: "Earned Leave",
  COL: "Commuted Leave",
  VL: "Vacation Leave",
};

const CATEGORY_RULES: Record<LeaveCategory, string> = {
  CL: "8 days/year. Half-days supported. Lapses at year end.",
  RH: "2 days/year. Must match published RH list. Lapses at year end.",
  SCL: "Up to 15 days/year. Admissible by Sanctioning Authority. Lapses.",
  EL: "30 days/year (Staff). Continuous calendar counting. Carries forward.",
  COL: "20 days/year. Continuous counting. Carries forward.",
  VL: "60 days/year (Faculty). Unused balance converts 2:1 to EL at year end.",
};

export function LeaveBalancesView() {
  const currentYear = new Date().getFullYear();
  const { data: balances, isPending } = useBalances(currentYear);

  if (isPending) {
    return (
      <Center py="xl">
        <Loader size="md" />
      </Center>
    );
  }

  return (
    <Stack gap="lg">
      <Alert icon={<FaInfoCircle size={16} />} title="Institutional Entitlement Policy" color="blue" radius="md">
        Entitlements are calculated according to ELM Baseline Specifications (v1.4). Unused CL, RH, and SCL
        lapse annually on December 31. Faculty Vacation Leave (VL) converts at 2:1 to EL, while EL and COL carry forward.
      </Alert>

      <Grid>
        {balances?.map((b) => {
          const credited = parseFloat(b.credited);
          const availed = parseFloat(b.availed);
          const balance = parseFloat(b.balance);
          const percent = credited > 0 ? Math.min(100, (availed / credited) * 100) : 0;

          return (
            <Grid.Col key={b.id} span={{ base: 12, sm: 6, md: 4 }}>
              <Card withBorder padding="md" radius="md">
                <Stack gap="xs">
                  <Group justify="space-between" align="center">
                    <Group gap="xs">
                      <FaWallet color="#1c7ed6" />
                      <Title order={4}>{b.leave_type}</Title>
                    </Group>
                    <Text size="xs" fw={700} c={balance > 0 ? "teal" : "red"}>
                      {balance.toFixed(1)} Available
                    </Text>
                  </Group>

                  <Text size="xs" fw={500} c="dimmed">
                    {CATEGORY_NAMES[b.leave_type] ?? b.leave_type}
                  </Text>

                  <Progress value={percent} size="sm" radius="xl" color={percent > 80 ? "red" : "blue"} />

                  <Group justify="space-between" pt="xs">
                    <div>
                      <Text size="xs" c="dimmed">Credited</Text>
                      <Text size="sm" fw={600}>{credited.toFixed(1)}</Text>
                    </div>
                    <div>
                      <Text size="xs" c="dimmed">Availed</Text>
                      <Text size="sm" fw={600}>{availed.toFixed(1)}</Text>
                    </div>
                    <div>
                      <Text size="xs" c="dimmed">Balance</Text>
                      <Text size="sm" fw={700} c="blue">{balance.toFixed(1)}</Text>
                    </div>
                  </Group>

                  <Text size="xs" c="dimmed" mt={4} style={{ minHeight: "2.4em" }}>
                    {CATEGORY_RULES[b.leave_type] ?? ""}
                  </Text>
                </Stack>
              </Card>
            </Grid.Col>
          );
        })}
      </Grid>
    </Stack>
  );
}
