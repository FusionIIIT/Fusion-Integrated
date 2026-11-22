import { useEffect, useState } from "react";
import {
  Badge,
  Card,
  Container,
  Grid,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { PageHeader } from "../../../ui/components/PageHeader";
import { leaveApi } from "../api/client";
import type { HolidayItem, VacationPeriodItem } from "../api/types";

export default function CalendarPage() {
  const [loading, setLoading] = useState(true);
  const [holidays, setHolidays] = useState<HolidayItem[]>([]);
  const [vacations, setVacations] = useState<VacationPeriodItem[]>([]);

  useEffect(() => {
    const fetchCalendar = async () => {
      try {
        setLoading(true);
        const data = await leaveApi.getCalendar();
        setHolidays(data.holidays);
        setVacations(data.vacation_periods);
      } catch (err) {
        notifications.show({ title: "Error", message: errorMessage(err), color: "red" });
      } finally {
        setLoading(false);
      }
    };
    fetchCalendar();
  }, []);

  return (
    <Container size="xl">
      <PageHeader
        title="Holiday & Vacation Calendar"
        subtitle="Published closed holidays, restricted holidays (RH), and faculty vacation windows."
      />

      <Grid>
        <Grid.Col span={{ base: 12, md: 7 }}>
          <Title order={4} mb="md">Published Holidays & RH</Title>
          <Card padding="md" shadow="sm" radius="md" withBorder>
            <DataTable<HolidayItem>
              rows={holidays}
              loading={loading}
              rowKey={(r) => r.id}
              empty={{ title: "No holidays published", description: "No holidays have been published for this calendar year." }}
              columns={[
                { key: "date", header: "Date", render: (r) => r.date },
                { key: "name", header: "Name", render: (r) => r.name },
                {
                  key: "kind",
                  header: "Type",
                  render: (r) => (
                    <Badge color={r.kind === "closed" ? "red" : "blue"}>
                      {r.kind === "closed" ? "Closed Holiday" : "Restricted Holiday"}
                    </Badge>
                  ),
                },
              ]}
            />
          </Card>
        </Grid.Col>

        <Grid.Col span={{ base: 12, md: 5 }}>
          <Title order={4} mb="md">Faculty Vacation Periods (EXT-01)</Title>
          <Card padding="md" shadow="sm" radius="md" withBorder>
            <DataTable<VacationPeriodItem>
              rows={vacations}
              loading={loading}
              rowKey={(r) => r.id}
              empty={{ title: "No vacation periods", description: "No academic vacation periods currently scheduled." }}
              columns={[
                { key: "name", header: "Period", render: (r) => r.name },
                { key: "dates", header: "Dates", render: (r) => `${r.start_date} → ${r.end_date}` },
              ]}
            />
          </Card>
        </Grid.Col>
      </Grid>
    </Container>
  );
}
