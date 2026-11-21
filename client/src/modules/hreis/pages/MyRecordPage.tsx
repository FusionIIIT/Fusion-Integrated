import { Alert, Card, Container, Grid, Stack, Text } from "@mantine/core";

import { errorStatus } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useMyServiceRecord } from "../api/hooks";

export default function MyRecordPage() {
  const { data, error, isPending } = useMyServiceRecord();
  return (
    <Container size="lg">
      <PageHeader title="My Service Record"
        subtitle="Your official HR information, available here in read-only form" />
      {isPending && <Text c="dimmed">Loading your service record...</Text>}
      {error && errorStatus(error) === 404 && (
        <Alert color="blue" title="No service record available">
          HR Administration has not yet published an accessible record for you.
        </Alert>
      )}
      {error && errorStatus(error) !== 404 && <ErrorState error={error} />}
      {data && (
        <Stack gap="md">
          <Grid>
            {([
              ["Department", data.department],
              ["Designation", data.designation_snapshot],
              ["Retirement status", data.retirement_status || "Not recorded"],
              ["Record revision", String(data.revision)],
            ] as const).map(([label, value]) => (
              <Grid.Col span={{ base: 12, sm: 6 }} key={label}>
                <Card withBorder padding="md">
                  <Text size="xs" c="dimmed" tt="uppercase">{label}</Text>
                  <Text fw={600}>{value}</Text>
                </Card>
              </Grid.Col>
            ))}
          </Grid>
          <Card withBorder padding="lg">
            <Text fw={700} mb="sm">Appointment details</Text>
            {Object.keys(data.appointment_details).length === 0
              ? <Text c="dimmed">No appointment details recorded.</Text>
              : Object.entries(data.appointment_details).map(([label, value]) => (
                <Grid key={label} mb="xs">
                  <Grid.Col span={4}><Text c="dimmed" size="sm">{label}</Text></Grid.Col>
                  <Grid.Col span={8}><Text size="sm">{String(value ?? "")}</Text></Grid.Col>
                </Grid>
              ))}
          </Card>
          <Card withBorder padding="lg">
            <Text fw={700} mb="sm">Verified leave balances</Text>
            {Object.keys(data.leave_balances ?? {}).length === 0
              ? <Text c="dimmed">No verified leave credits have been recorded.</Text>
              : Object.entries(data.leave_balances ?? {}).map(([leaveType, amount]) => (
                <Grid key={leaveType} mb="xs">
                  <Grid.Col span={8}><Text size="sm">{leaveType}</Text></Grid.Col>
                  <Grid.Col span={4}><Text fw={600}>{amount} days</Text></Grid.Col>
                </Grid>
              ))}
          </Card>
          <Card withBorder padding="lg">
            <Text fw={700} mb="sm">Service history</Text>
            {data.service_history.length === 0
              ? <Text c="dimmed">No service-history entries recorded.</Text>
              : data.service_history.map((item, index) => (
                <Text size="sm" key={index} mb="xs">
                  {typeof item === "string" ? item : JSON.stringify(item)}
                </Text>
              ))}
          </Card>
        </Stack>
      )}
    </Container>
  );
}
