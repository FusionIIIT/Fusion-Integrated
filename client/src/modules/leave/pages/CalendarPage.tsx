import { useState } from "react";
import {
  Alert,
  Badge,
  Card,
  Container,
  Group,
  Paper,
  SegmentedControl,
  SimpleGrid,
  Stack,
  Text,
  ThemeIcon,
} from "@mantine/core";
import {
  FaCalendarAlt,
  FaCalendarCheck,
  FaCalendarDay,
  FaInfoCircle,
} from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { DataTable } from "../../../ui/components/DataTable";
import { PageHeader } from "../../../ui/components/PageHeader";

interface HolidayItem {
  id: number;
  date: string;
  name: string;
  type: "gazetted" | "restricted";
  description?: string;
}

const SAMPLE_HOLIDAYS_2026: HolidayItem[] = [
  { id: 1, date: "2026-01-26", name: "Republic Day", type: "gazetted", description: "National Holiday" },
  { id: 2, date: "2026-02-15", name: "Maha Shivratri", type: "gazetted" },
  { id: 3, date: "2026-03-04", name: "Holi", type: "gazetted" },
  { id: 4, date: "2026-03-20", name: "Id-ul-Fitr", type: "gazetted" },
  { id: 5, date: "2026-04-03", name: "Good Friday", type: "gazetted" },
  { id: 6, date: "2026-04-14", name: "Dr. B.R. Ambedkar Jayanti", type: "restricted", description: "Restricted Holiday" },
  { id: 7, date: "2026-05-01", name: "Buddha Purnima", type: "gazetted" },
  { id: 8, date: "2026-06-17", name: "Bakrid / Id-ul-Zuha", type: "gazetted" },
  { id: 9, date: "2026-07-17", name: "Muharram", type: "gazetted" },
  { id: 10, date: "2026-08-15", name: "Independence Day", type: "gazetted", description: "National Holiday" },
  { id: 11, date: "2026-08-28", name: "Raksha Bandhan", type: "restricted", description: "Restricted Holiday" },
  { id: 12, date: "2026-09-04", name: "Janmashtami", type: "gazetted" },
  { id: 13, date: "2026-10-02", name: "Mahatma Gandhi Jayanti", type: "gazetted", description: "National Holiday" },
  { id: 14, date: "2026-10-20", name: "Dussehra (Vijay Dashami)", type: "gazetted" },
  { id: 15, date: "2026-11-09", name: "Diwali (Deepavali)", type: "gazetted" },
  { id: 16, date: "2026-11-10", name: "Govardhan Puja", type: "restricted", description: "Restricted Holiday" },
  { id: 17, date: "2026-11-24", name: "Guru Nanak Jayanti", type: "gazetted" },
  { id: 18, date: "2026-12-25", name: "Christmas Day", type: "gazetted" },
];

export default function CalendarPage() {
  const { can } = useAuth();
  const canManagePolicy = can("leave.type.manage");
  const [filter, setFilter] = useState<"all" | "gazetted" | "restricted">("all");

  const filtered = filter === "all"
    ? SAMPLE_HOLIDAYS_2026
    : SAMPLE_HOLIDAYS_2026.filter((h) => h.type === filter);

  const gazettedCount = SAMPLE_HOLIDAYS_2026.filter((h) => h.type === "gazetted").length;
  const restrictedCount = SAMPLE_HOLIDAYS_2026.filter((h) => h.type === "restricted").length;

  return (
    <Container size="xl">
      <PageHeader
        title="Institute Holiday & RH Calendar"
        subtitle="Published holiday schedule for the calendar year 2026 used for leave date calculations and RH entitlements."
      />

      <SimpleGrid cols={{ base: 1, sm: 3 }} mb="lg" spacing="md">
        <Paper withBorder p="md" radius="md">
          <Group justify="space-between">
            <div>
              <Text size="xs" c="dimmed">Gazetted Holidays</Text>
              <Text size="xl" fw={800} c="blue">{gazettedCount}</Text>
            </div>
            <ThemeIcon color="blue" variant="light" size="lg">
              <FaCalendarCheck />
            </ThemeIcon>
          </Group>
          <Text size="xs" c="dimmed" mt="xs">
            Closed institute holidays; excluded from Casual Leave counts.
          </Text>
        </Paper>

        <Paper withBorder p="md" radius="md">
          <Group justify="space-between">
            <div>
              <Text size="xs" c="dimmed">Restricted Holidays (RH)</Text>
              <Text size="xl" fw={800} c="orange">{restrictedCount}</Text>
            </div>
            <ThemeIcon color="orange" variant="light" size="lg">
              <FaCalendarDay />
            </ThemeIcon>
          </Group>
          <Text size="xs" c="dimmed" mt="xs">
            Optional festival holidays (quota: 2 days/year per eligible employee).
          </Text>
        </Paper>

        <Paper withBorder p="md" radius="md">
          <Group justify="space-between">
            <div>
              <Text size="xs" c="dimmed">Calendar Year</Text>
              <Text size="xl" fw={800} c="indigo">2026</Text>
            </div>
            <ThemeIcon color="indigo" variant="light" size="lg">
              <FaCalendarAlt />
            </ThemeIcon>
          </Group>
          <Text size="xs" c="dimmed" mt="xs">
            Effective published calendar in sync with Fusion ERP directory.
          </Text>
        </Paper>
      </SimpleGrid>

      {canManagePolicy && (
        <Alert color="blue" icon={<FaInfoCircle />} mb="lg" title="Administrative Authority Notice">
          <Text size="sm">
            As an authorized Leave Administrator, holiday definitions and calendar parameters govern
            automated continuous counting vs working-day counts for all employee leave requests.
          </Text>
        </Alert>
      )}

      <Card withBorder padding="lg" radius="md">
        <Group justify="space-between" mb="md" wrap="wrap">
          <Text fw={700} size="md">List of Institute Holidays</Text>
          <SegmentedControl
            size="xs"
            value={filter}
            onChange={(val) => setFilter(val as any)}
            data={[
              { value: "all", label: `All (${SAMPLE_HOLIDAYS_2026.length})` },
              { value: "gazetted", label: `Gazetted (${gazettedCount})` },
              { value: "restricted", label: `Restricted (${restrictedCount})` },
            ]}
          />
        </Group>

        <DataTable<HolidayItem>
          rows={filtered}
          rowKey={(r) => r.id}
          minWidth={700}
          columns={[
            {
              key: "date",
              header: "Date",
              render: (r) => (
                <Text fw={600} size="sm">
                  {new Date(r.date).toLocaleDateString(undefined, {
                    weekday: "short",
                    year: "numeric",
                    month: "short",
                    day: "numeric",
                  })}
                </Text>
              ),
            },
            {
              key: "name",
              header: "Holiday Name",
              render: (r) => (
                <Stack gap={0}>
                  <Text fw={600} size="sm">{r.name}</Text>
                  {r.description && <Text size="xs" c="dimmed">{r.description}</Text>}
                </Stack>
              ),
            },
            {
              key: "type",
              header: "Category",
              render: (r) => (
                <Badge color={r.type === "gazetted" ? "blue" : "orange"} variant="light" size="sm">
                  {r.type.toUpperCase()}
                </Badge>
              ),
            },
          ]}
          empty={{
            icon: FaCalendarAlt,
            title: "No holidays match the filter",
            description: "Try switching the filter above.",
          }}
        />
      </Card>
    </Container>
  );
}
