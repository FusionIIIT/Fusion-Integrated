import { useState, useEffect } from "react";
import {
  Container, Group, Paper, SimpleGrid, Text, ThemeIcon
} from "@mantine/core";
import {
  FaFlask, FaBriefcase, FaMoneyBillWave, FaShoppingCart, FaChartBar
} from "react-icons/fa";
import { PageHeader } from "../../../ui/components/PageHeader";

export default function ReportsPage() {
  const [stats, setStats] = useState<{
    proposals?: number;
    consultancy?: number;
    finance_requests?: number;
    procurement_requests?: number;
    progress_reports?: number;
  }>({});

  useEffect(() => {
    fetch("/api/v1/rspc/dashboard", { credentials: "include" })
      .then((r) => r.json())
      .then((data) => setStats(data))
      .catch(() => {});
  }, []);

  const cards = [
    { title: "Research Proposals", value: stats.proposals ?? 0, icon: FaFlask, color: "blue" },
    { title: "Consultancy Projects", value: stats.consultancy ?? 0, icon: FaBriefcase, color: "teal" },
    { title: "Financial Requests", value: stats.finance_requests ?? 0, icon: FaMoneyBillWave, color: "green" },
    { title: "Procurement Requests", value: stats.procurement_requests ?? 0, icon: FaShoppingCart, color: "orange" },
    { title: "Progress Reports", value: stats.progress_reports ?? 0, icon: FaChartBar, color: "grape" },
  ];

  return (
    <Container size="xl">
      <PageHeader
        title="RSPC Overview & Statistics"
        subtitle="Operational metrics across all active research, consultancy, and procurement workflows"
      />

      <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="lg" mt="md">
        {cards.map((c) => {
          const Icon = c.icon;
          return (
            <Paper key={c.title} withBorder p="md" radius="md">
              <Group justify="space-between">
                <Text size="xs" c="dimmed" fw={700} tt="uppercase">
                  {c.title}
                </Text>
                <ThemeIcon color={c.color} variant="light" size="lg" radius="md">
                  <Icon size={18} />
                </ThemeIcon>
              </Group>

              <Group align="flex-end" gap="xs" mt={25}>
                <Text fw={700} size="xl">{c.value}</Text>
              </Group>
              <Text size="xs" c="dimmed" mt={7}>
                Records tracked in system
              </Text>
            </Paper>
          );
        })}
      </SimpleGrid>
    </Container>
  );
}
