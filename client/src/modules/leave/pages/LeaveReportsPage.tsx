import { useState } from "react";
import { Button, Card, Container, Group, Stack, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useYearEndProcessing } from "../hooks/useLeaveRequests";

export default function LeaveReportsPage() {
  const [year, setYear] = useState(() => new Date().getFullYear());
  const yearEnd = useYearEndProcessing();

  const handleYearEnd = async () => {
    if (!window.confirm(`Run year-end processing for ${year}? This will process all leave balances.`)) return;
    try {
      const result = await yearEnd.mutateAsync(year);
      notifications.show({
        title: "Year-End Processing Complete",
        message: `Processed ${result.processed_users} users. ${result.errors.length} errors.`,
        color: result.errors.length === 0 ? "green" : "orange",
      });
    } catch {
      notifications.show({ title: "Error", message: "Year-end processing failed", color: "red" });
    }
  };

  const years = Array.from({ length: 5 }, (_, i) => new Date().getFullYear() - i);

  return (
    <Container size="xl">
      <PageHeader title="Year-End Processing" subtitle="Process year-end leave balances" />
      <Card padding="lg">
        <Stack gap="md">
          <Text fw={600} size="lg">Year-End Processing</Text>
          <Text c="dimmed">
            Run year-end processing to apply lapse rules, convert unused faculty VL to EL, and carry forward applicable balances.
          </Text>
          <Group>
            <select
              value={year}
              onChange={(event) => setYear(Number(event.currentTarget.value))}
              className="mantine-Input-input"
              style={{ width: 150 }}
            >
              {years.map((value) => (
                <option key={value} value={value}>{value}</option>
              ))}
            </select>
            <Button onClick={handleYearEnd} loading={yearEnd.isPending} color="blue">
              Run Year-End Processing
            </Button>
          </Group>
        </Stack>
      </Card>
    </Container>
  );
}
