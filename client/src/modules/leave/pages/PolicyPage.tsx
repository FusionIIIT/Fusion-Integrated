import { useState } from "react";
import {
  Badge, Button, Card, Container, Group, Stack, Tabs, Text,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCog, FaRegCalendarAlt } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { formatDay } from "../components/PeriodCell";
import {
  useCalendars, useHolidays, usePolicies, usePolicyRules, usePublishCalendar,
  usePublishPolicy, useVacations,
} from "../api/hooks";
import type {
  Calendar, CategoryRule, Holiday, Policy, VacationPeriod,
} from "../api/types";

/** Entitlement, counting and the calendar are configuration, not code. A
 *  published version is never edited — it is superseded — because requests
 *  already decided cite the version they were decided under. */
export default function PolicyPage() {
  const policies = usePolicies();
  const calendars = useCalendars();
  const publishPolicy = usePublishPolicy();
  const publishCalendar = usePublishCalendar();
  const [policyId, setPolicyId] = useState<number | null>(null);
  const [calendarId, setCalendarId] = useState<number | null>(null);
  const rules = usePolicyRules(policyId);
  const holidays = useHolidays(calendarId);
  const vacations = useVacations(calendarId);

  if (policies.error) {
    return <Container size="xl"><ErrorState error={policies.error} /></Container>;
  }

  function publish(run: Promise<unknown>, what: string) {
    run
      .then(() => notifications.show({
        color: "green", title: "Published",
        message: `${what} is now in force.`,
      }))
      .catch((e) => notifications.show({
        color: "red", title: "Not published", message: errorMessage(e),
      }));
  }

  return (
    <Container size="xl">
      <PageHeader
        title="Policy & Calendar"
        subtitle="What the module counts, credits and treats as a working day"
      />

      <Tabs defaultValue="policy">
        <Tabs.List mb="md">
          <Tabs.Tab value="policy" leftSection={<FaCog size={12} />}>
            Policy versions
          </Tabs.Tab>
          <Tabs.Tab value="calendar" leftSection={<FaRegCalendarAlt size={12} />}>
            Calendars
          </Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="policy">
          <Stack gap="lg">
            <Card padding="lg">
              <DataTable<Policy>
                rows={policies.data ?? []} loading={policies.isPending}
                rowKey={(r) => r.id} minWidth={860}
                columns={[
                  { key: "version", header: "Version", render: (r) => r.version },
                  { key: "effective", header: "In force",
                    render: (r) => `${formatDay(r.effective_from)} — ${
                      r.effective_to ? formatDay(r.effective_to) : "open"}` },
                  { key: "conversion", header: "VL to EL",
                    render: (r) => `${r.vl_to_el_ratio} : 1 · ${
                      r.vl_to_el_rounding.toLowerCase().replace(/_/g, " ")}` },
                  { key: "tail", header: "Early return",
                    render: (r) => r.early_return_tail.toLowerCase().replace(/_/g, " ") },
                  { key: "published", header: "Status",
                    render: (r) => (
                      <Badge color={r.published ? "green" : "gray"} variant="light">
                        {r.published ? "published" : "draft"}
                      </Badge>
                    ) },
                  {
                    key: "actions", header: "", align: "right",
                    render: (r) => (
                      <Group justify="flex-end" gap="xs">
                        <Button
                          size="xs" variant="subtle" color="gray"
                          onClick={() => setPolicyId(r.id)}
                        >
                          Rules
                        </Button>
                        {!r.published && (
                          <Button
                            size="xs" loading={publishPolicy.isPending}
                            onClick={() => publish(
                              publishPolicy.mutateAsync(r.id), `Policy ${r.version}`)}
                          >
                            Publish
                          </Button>
                        )}
                      </Group>
                    ),
                  },
                ]}
                empty={{ icon: FaCog, title: "No policy versions" }}
              />
            </Card>

            {policyId && (
              <Card padding="lg">
                <Text fw={600} mb="md">Entitlement by category</Text>
                <DataTable<CategoryRule>
                  rows={rules.data ?? []} loading={rules.isPending}
                  rowKey={(r) => r.id} minWidth={720}
                  columns={[
                    { key: "category", header: "Category", render: (r) => r.category },
                    { key: "annual_credit", header: "Credited a year",
                      align: "right", render: (r) => r.annual_credit },
                    { key: "carry", header: "Carries forward",
                      render: (r) => r.carries_forward
                        ? `yes${r.carry_forward_cap ? `, capped at ${r.carry_forward_cap}` : ""}`
                        : "no" },
                    { key: "who", header: "Applies to",
                      render: (r) => r.applies_to_faculty == null
                        ? "everyone"
                        : r.applies_to_faculty ? "faculty" : "non-faculty" },
                  ]}
                  empty={{ icon: FaCog, title: "This version defines no rules" }}
                />
              </Card>
            )}
          </Stack>
        </Tabs.Panel>

        <Tabs.Panel value="calendar">
          <Stack gap="lg">
            <Card padding="lg">
              <DataTable<Calendar>
                rows={calendars.data ?? []} loading={calendars.isPending}
                rowKey={(r) => r.id} minWidth={640}
                columns={[
                  { key: "year", header: "Year", render: (r) => r.year },
                  { key: "version", header: "Version", render: (r) => r.version },
                  { key: "published", header: "Status",
                    render: (r) => (
                      <Badge color={r.published ? "green" : "gray"} variant="light">
                        {r.published ? "published" : "draft"}
                      </Badge>
                    ) },
                  {
                    key: "actions", header: "", align: "right",
                    render: (r) => (
                      <Group justify="flex-end" gap="xs">
                        <Button
                          size="xs" variant="subtle" color="gray"
                          onClick={() => setCalendarId(r.id)}
                        >
                          Open
                        </Button>
                        {!r.published && (
                          <Button
                            size="xs" loading={publishCalendar.isPending}
                            onClick={() => publish(
                              publishCalendar.mutateAsync(r.id),
                              `The ${r.year} calendar`)}
                          >
                            Publish
                          </Button>
                        )}
                      </Group>
                    ),
                  },
                ]}
                empty={{ icon: FaRegCalendarAlt, title: "No calendars" }}
              />
            </Card>

            {calendarId && (
              <>
                <Card padding="lg">
                  <Text fw={600} mb="md">Holidays</Text>
                  <DataTable<Holiday>
                    rows={holidays.data ?? []} loading={holidays.isPending}
                    rowKey={(r) => r.id} minWidth={640}
                    columns={[
                      { key: "day", header: "Date", render: (r) => formatDay(r.day) },
                      { key: "name", header: "Occasion", render: (r) => r.name },
                      { key: "restricted", header: "Kind",
                        render: (r) => (
                          <Badge variant="light" color={r.restricted ? "grape" : "blue"}>
                            {r.restricted ? "restricted" : "closed holiday"}
                          </Badge>
                        ) },
                    ]}
                    empty={{ icon: FaRegCalendarAlt, title: "No holidays listed" }}
                  />
                </Card>

                <Card padding="lg">
                  <Text fw={600} mb="md">Vacation periods</Text>
                  <DataTable<VacationPeriod>
                    rows={vacations.data ?? []} loading={vacations.isPending}
                    rowKey={(r) => r.id} minWidth={640}
                    columns={[
                      { key: "name", header: "Period", render: (r) => r.name },
                      { key: "starts_on", header: "From",
                        render: (r) => formatDay(r.starts_on) },
                      { key: "ends_on", header: "To",
                        render: (r) => formatDay(r.ends_on) },
                    ]}
                    empty={{
                      icon: FaRegCalendarAlt,
                      title: "No vacation periods",
                      description: "Vacation leave cannot be applied for without one.",
                    }}
                  />
                </Card>
              </>
            )}
          </Stack>
        </Tabs.Panel>
      </Tabs>
    </Container>
  );
}
