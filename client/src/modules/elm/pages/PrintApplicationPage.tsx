import { useState } from "react";
import { Alert, Button, Card, Container, Select, Stack, Text } from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useLeaveHistory, usePrintApplication } from "../api/hooks";

export default function PrintApplicationPage() {
  const historyQuery = useLeaveHistory();
  const applications = (historyQuery.data ?? [])
    .filter((entry) => entry.type === "application" && entry.pk !== undefined);
  const [selected, setSelected] = useState<string | null>(null);
  const applicationId = Number(selected ?? 0);
  const printQuery = usePrintApplication(applicationId);

  if (historyQuery.error) {
    return <Container size="md"><ErrorState error={historyQuery.error} /></Container>;
  }
  if (printQuery.error) {
    return <Container size="md"><ErrorState error={printQuery.error} /></Container>;
  }

  const printData = printQuery.data?.print_data;
  const app = printQuery.data?.application;
  const options = applications.map((entry) => ({
    value: String(entry.pk),
    label: (entry.leave_category_code ?? "Leave") + " · "
      + (entry.requested_start ?? "date unavailable"),
  }));

  return (
    <Container size="md">
      <PageHeader title="Print Leave Application" />
      {options.length === 0 ? (
        <Alert color="gray">Submit an application before printing it.</Alert>
      ) : (
        <Stack>
          <Select
            label="Application"
            placeholder="Choose an application"
            data={options}
            value={selected}
            onChange={setSelected}
          />
          {app && printData && (
            <Card withBorder>
              <Stack>
                <Text fw={600}>Application ELM-{app.pk}</Text>
                <Text>Category: {app.leave_category_label}</Text>
                <Text>
                  Period: {app.requested_start} – {app.requested_end}
                </Text>
                {app.day_part !== "full_day" && (
                  <Text>Day portion: {app.day_part === "first_half" ? "First half" : "Second half"}</Text>
                )}
                <Text>Purpose: {app.purpose_reason || "Not specified"}</Text>
                <Text>Status: {app.status}</Text>
                {app.station_leave && (
                  <Text>Station Leave: {app.station_details || "Details not provided"}</Text>
                )}
                <Button onClick={() => window.print()}>Print / Save as PDF</Button>
              </Stack>
            </Card>
          )}
        </Stack>
      )}
    </Container>
  );
}
