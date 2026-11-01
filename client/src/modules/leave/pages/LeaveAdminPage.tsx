import {
  Alert,
  Badge,
  Box,
  Button,
  Card,
  Grid,
  Group,
  NumberInput,
  Paper,
  Select,
  Stack,
  Table,
  Tabs,
  Text,
  Textarea,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import React, { useEffect, useState } from "react";
import { leaveApi } from "../api";
import type { HolidayCalendar, VacationPeriod } from "../types";

export const LeaveAdminPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string | null>("calendar");
  const [holidays, setHolidays] = useState<HolidayCalendar[]>([]);
  const [vacations, setVacations] = useState<VacationPeriod[]>([]);
  const [loading, setLoading] = useState(true);

  // Offline Sync state
  const [offlineUid, setOfflineUid] = useState<number | "">("");
  const [offlineCat, setOfflineCat] = useState("CL");
  const [offlineStart, setOfflineStart] = useState("");
  const [offlineEnd, setOfflineEnd] = useState("");
  const [offlineReason, setOfflineReason] = useState("");
  const [offlineRef, setOfflineRef] = useState("");
  const [syncLoading, setSyncLoading] = useState(false);

  // Year End state
  const [yearEndYear, setYearEndYear] = useState<number>(new Date().getFullYear());
  const [yearEndReport, setYearEndReport] = useState<Record<string, unknown> | null>(null);
  const [yearEndLoading, setYearEndLoading] = useState(false);

  const loadCalendars = async () => {
    setLoading(true);
    try {
      const [hols, vacs] = await Promise.all([
        leaveApi.getHolidayCalendar(),
        leaveApi.getVacationPeriods(),
      ]);
      setHolidays(hols);
      setVacations(vacs);
    } catch {
      notifications.show({ title: "Error", message: "Failed to load calendar data.", color: "red" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCalendars();
  }, []);

  const handleOfflineSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!offlineUid || !offlineStart || !offlineEnd || !offlineRef) {
      notifications.show({ title: "Validation Error", message: "Please fill all required fields.", color: "red" });
      return;
    }
    setSyncLoading(true);
    try {
      await leaveApi.recordOfflineLeave({
        user_id: Number(offlineUid),
        category: offlineCat,
        start_date: offlineStart,
        end_date: offlineEnd,
        reason: offlineReason,
        offline_reference: offlineRef,
      });
      notifications.show({
        title: "Synchronized",
        message: "Offline leave successfully recorded and balance updated.",
        color: "teal",
      });
      setOfflineUid("");
      setOfflineStart("");
      setOfflineEnd("");
      setOfflineReason("");
      setOfflineRef("");
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: string } } })?.response?.data?.error || "Offline sync failed";
      notifications.show({ title: "Error", message: msg, color: "red" });
    } finally {
      setSyncLoading(false);
    }
  };

  const handleYearEndExecute = async () => {
    setYearEndLoading(true);
    try {
      const res = await leaveApi.executeYearEnd(yearEndYear);
      setYearEndReport(res);
      notifications.show({
        title: "Year-End Processed",
        message: `Year-end boundary processing for ${yearEndYear} completed.`,
        color: "teal",
      });
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: string } } })?.response?.data?.error || "Year-end processing failed";
      notifications.show({ title: "Error", message: msg, color: "red" });
    } finally {
      setYearEndLoading(false);
    }
  };

  return (
    <Box p="md" maw={1000} mx="auto">
      <Title order={2} mb="xs">
        Leave Administration Console
      </Title>
      <Text c="dimmed" size="sm" mb="lg">
        Administer institute holiday/RH calendars, retrospectively record offline-sanctioned leave,
        and execute year-end leave account conversions.
      </Text>

      <Tabs value={activeTab} onChange={setActiveTab}>
        <Tabs.List mb="md">
          <Tabs.Tab value="calendar">Calendars & Vacation Periods</Tabs.Tab>
          <Tabs.Tab value="offline">Record Offline Leave</Tabs.Tab>
          <Tabs.Tab value="yearend">Year-End Processing</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="calendar">
          <Paper withBorder p="md" shadow="xs" radius="md">
            <Title order={4} mb="xs">
              Published Holiday & Restricted Holiday Calendar (BR-EL-031)
            </Title>
            <Text size="sm" c="dimmed" mb="md">
              Restricted Holiday applications (RH) can only be booked on dates designated as Restricted Holiday (RH).
            </Text>
            {holidays.length === 0 ? (
              <Text c="dimmed" py="md">No published holidays for current year.</Text>
            ) : (
              <Table striped highlightOnHover mb="xl">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Date</Table.Th>
                    <Table.Th>Holiday Name</Table.Th>
                    <Table.Th>Type</Table.Th>
                    <Table.Th>Status</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {holidays.map((h) => (
                    <Table.Tr key={h.id}>
                      <Table.Td>{h.date}</Table.Td>
                      <Table.Td>{h.name}</Table.Td>
                      <Table.Td>
                        <Badge color={h.is_restricted ? "orange" : "blue"}>
                          {h.is_restricted ? "Restricted Holiday (RH)" : "Closed Holiday"}
                        </Badge>
                      </Table.Td>
                      <Table.Td>
                        <Badge color="teal" variant="light">
                          Published
                        </Badge>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            )}

            <Title order={4} mb="xs">
              Academic Calendar Vacation Periods (BR-EL-006)
            </Title>
            <Text size="sm" c="dimmed" mb="md">
              Faculty Vacation Leave (VL) must fall within these published dates.
            </Text>
            {vacations.length === 0 ? (
              <Text c="dimmed" py="md">No active vacation periods recorded.</Text>
            ) : (
              <Table striped highlightOnHover>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Period Name</Table.Th>
                    <Table.Th>Start Date</Table.Th>
                    <Table.Th>End Date</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {vacations.map((v) => (
                    <Table.Tr key={v.id}>
                      <Table.Td>{v.name}</Table.Td>
                      <Table.Td>{v.start_date}</Table.Td>
                      <Table.Td>{v.end_date}</Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            )}
          </Paper>
        </Tabs.Panel>

        <Tabs.Panel value="offline">
          <Paper withBorder p="md" shadow="xs" radius="md">
            <Title order={4} mb="xs">
              Record Already-Sanctioned Offline Leave (BR-EL-029)
            </Title>
            <Text size="sm" c="dimmed" mb="md">
              Retrospectively synchronize leave already authorized through a valid paper/offline route
              when ELM was unavailable. This updates records and balances without initiating a second workflow.
            </Text>

            <form onSubmit={handleOfflineSubmit}>
              <Stack gap="md">
                <Grid>
                  <Grid.Col span={6}>
                    <NumberInput
                      label="Employee User ID"
                      required
                      placeholder="e.g. 1001"
                      value={offlineUid}
                      onChange={(v) => setOfflineUid(v === "" ? "" : Number(v))}
                    />
                  </Grid.Col>
                  <Grid.Col span={6}>
                    <Select
                      label="Category"
                      required
                      data={["CL", "RH", "SCL", "EL", "COL", "VL"]}
                      value={offlineCat}
                      onChange={(v) => setOfflineCat(v || "CL")}
                    />
                  </Grid.Col>
                </Grid>

                <Grid>
                  <Grid.Col span={6}>
                    <TextInput
                      label="Start Date"
                      type="date"
                      required
                      value={offlineStart}
                      onChange={(e) => setOfflineStart(e.target.value)}
                    />
                  </Grid.Col>
                  <Grid.Col span={6}>
                    <TextInput
                      label="End Date"
                      type="date"
                      required
                      value={offlineEnd}
                      onChange={(e) => setOfflineEnd(e.target.value)}
                    />
                  </Grid.Col>
                </Grid>

                <TextInput
                  label="Offline Sanction Order / File Reference"
                  required
                  placeholder="e.g. IIITDMJ/DIR/OFFLINE-LEAVE/2026/042"
                  value={offlineRef}
                  onChange={(e) => setOfflineRef(e.target.value)}
                />

                <Textarea
                  label="Reason / Notes"
                  placeholder="Context and details of offline leave..."
                  value={offlineReason}
                  onChange={(e) => setOfflineReason(e.target.value)}
                />

                <Group justify="flex-end">
                  <Button type="submit" loading={syncLoading} color="teal">
                    Record Offline Leave & Sync Balance
                  </Button>
                </Group>
              </Stack>
            </form>
          </Paper>
        </Tabs.Panel>

        <Tabs.Panel value="yearend">
          <Paper withBorder p="md" shadow="xs" radius="md">
            <Title order={4} mb="xs">
              Execute Year-End Leave Processing (BR-EL-007, BR-EL-008, EL-UC-020)
            </Title>
            <Text size="sm" c="dimmed" mb="md">
              At year end: unused CL, RH, and SCL lapse; unused faculty VL converts to EL at 2 VL : 1 EL;
              EL and COL carry forward into next calendar year.
            </Text>

            <Group align="flex-end" mb="lg">
              <NumberInput
                label="Target Calendar Year"
                value={yearEndYear}
                onChange={(v) => setYearEndYear(Number(v) || new Date().getFullYear())}
              />
              <Button color="orange" loading={yearEndLoading} onClick={handleYearEndExecute}>
                Run Year-End Processing
              </Button>
            </Group>

            {yearEndReport && (
              <Alert color="teal" title="Year-End Execution Summary">
                <Text size="sm">Lapsed Leave Days: {String(yearEndReport.lapsed ?? 0)}</Text>
                <Text size="sm">Carried Forward Days: {String(yearEndReport.carried_forward ?? 0)}</Text>
                <Text size="sm">
                  Faculty VL converted to EL: {String(yearEndReport.vl_converted_to_el ?? 0)}
                </Text>
              </Alert>
            )}
          </Paper>
        </Tabs.Panel>
      </Tabs>
    </Box>
  );
};

export default LeaveAdminPage;
