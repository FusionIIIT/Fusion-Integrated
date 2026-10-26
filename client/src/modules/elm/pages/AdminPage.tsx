import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  NumberInput,
  Select,
  SimpleGrid,
  Stack,
  Tabs,
  Text,
  TextInput,
  Textarea,
} from "@mantine/core";
import { DateInput } from "@mantine/dates";
import { notifications } from "@mantine/notifications";
import { FaCalendarAlt, FaCog, FaDatabase, FaUmbrellaBeach } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import {
  useAddHoliday,
  useAddVacation,
  useHolidays,
  useRecordOffline,
  useVacations,
} from "../api/hooks";
import {
  CATEGORY_LABELS,
  type Holiday,
  type VacationPeriod,
} from "../api/types";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";

const CATEGORY_OPTIONS = Object.entries(CATEGORY_LABELS).map(([v, l]) => ({
  value: v,
  label: l,
}));

export default function AdminPage() {
  const { data: holidaysData, isPending: holPending, error: holError } = useHolidays();
  const { data: vacationsData, isPending: vacPending, error: vacError } = useVacations();

  const addHoliday = useAddHoliday();
  const addVacation = useAddVacation();
  const recordOffline = useRecordOffline();

  // Holiday modal
  const [openHoliday, setOpenHoliday] = useState(false);
  const [holidayDate, setHolidayDate] = useState<Date | null>(null);
  const [holidayKind, setHolidayKind] = useState<string | null>("holiday");
  const [holidayLabel, setHolidayLabel] = useState("");

  // Vacation modal
  const [openVacation, setOpenVacation] = useState(false);
  const [vacationName, setVacationName] = useState("");
  const [vacStart, setVacStart] = useState<Date | null>(null);
  const [vacEnd, setVacEnd] = useState<Date | null>(null);

  // Offline leave modal
  const [openOffline, setOpenOffline] = useState(false);
  const [offlineUserId, setOfflineUserId] = useState<number | string>("");
  const [offlineKind, setOfflineKind] = useState<string | null>("faculty");
  const [offlineCategory, setOfflineCategory] = useState<string | null>("cl");
  const [offlineStart, setOfflineStart] = useState<Date | null>(null);
  const [offlineEnd, setOfflineEnd] = useState<Date | null>(null);
  const [offlineDept, setOfflineDept] = useState("CSE");
  const [offlineSanctionRef, setOfflineSanctionRef] = useState("");
  const [offlinePurpose, setOfflinePurpose] = useState("");

  if (holError) return <Container size="xl"><ErrorState error={holError} /></Container>;
  if (vacError) return <Container size="xl"><ErrorState error={vacError} /></Container>;

  function submitHoliday() {
    if (!holidayDate || !holidayKind) return;
    addHoliday.mutate(
      {
        date: holidayDate.toISOString().slice(0, 10),
        kind: holidayKind,
        label: holidayLabel,
        is_published: true,
      },
      {
        onSuccess: () => {
          notifications.show({ color: "green", title: "Holiday Published", message: "" });
          setOpenHoliday(false);
          setHolidayDate(null);
          setHolidayLabel("");
        },
        onError: (e) =>
          notifications.show({
            color: "red",
            title: "Could not add holiday",
            message: errorMessage(e),
          }),
      },
    );
  }

  function submitVacation() {
    if (!vacationName || !vacStart || !vacEnd) return;
    addVacation.mutate(
      {
        name: vacationName,
        start_date: vacStart.toISOString().slice(0, 10),
        end_date: vacEnd.toISOString().slice(0, 10),
        is_active: true,
      },
      {
        onSuccess: () => {
          notifications.show({ color: "green", title: "Vacation Period Added", message: "" });
          setOpenVacation(false);
          setVacationName("");
          setVacStart(null);
          setVacEnd(null);
        },
        onError: (e) =>
          notifications.show({
            color: "red",
            title: "Could not add vacation period",
            message: errorMessage(e),
          }),
      },
    );
  }

  function submitOffline() {
    if (!offlineUserId || !offlineCategory || !offlineStart || !offlineEnd || !offlineSanctionRef)
      return;

    recordOffline.mutate(
      {
        user_id: Number(offlineUserId),
        kind: offlineKind ?? "faculty",
        category: offlineCategory,
        start_date: offlineStart.toISOString().slice(0, 10),
        end_date: offlineEnd.toISOString().slice(0, 10),
        department: offlineDept,
        sanction_reference: offlineSanctionRef,
        purpose: offlinePurpose,
        half: "full",
      },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Offline Leave Synchronized",
            message: "Record created and balance updated.",
          });
          setOpenOffline(false);
          setOfflineUserId("");
          setOfflineSanctionRef("");
          setOfflinePurpose("");
        },
        onError: (e) =>
          notifications.show({
            color: "red",
            title: "Failed to record offline leave",
            message: errorMessage(e),
          }),
      },
    );
  }

  return (
    <Container size="xl">
      <PageHeader
        title="Leave Setup & Administration"
        subtitle="Holidays, academic vacation periods, and retrospective offline leave synchronization"
      />

      <Tabs defaultValue="holidays">
        <Tabs.List mb="md">
          <Tabs.Tab value="holidays" leftSection={<FaCalendarAlt size={14} />}>
            Holiday Calendar
          </Tabs.Tab>
          <Tabs.Tab value="vacations" leftSection={<FaUmbrellaBeach size={14} />}>
            Academic Vacations (VL)
          </Tabs.Tab>
          <Tabs.Tab value="offline" leftSection={<FaDatabase size={14} />}>
            Offline Leave Entry
          </Tabs.Tab>
        </Tabs.List>

        {/* Tab 1: Holidays */}
        <Tabs.Panel value="holidays">
          <Card padding="lg">
            <Group justify="space-between" mb="md">
              <Text fw={600} size="sm">
                Published Institute Holidays & Restricted Holidays
              </Text>
              <Button size="xs" onClick={() => setOpenHoliday(true)}>
                Add Holiday
              </Button>
            </Group>

            <DataTable<Holiday>
              rows={holidaysData?.results ?? []}
              loading={holPending}
              rowKey={(r) => r.id}
              columns={[
                { key: "date", header: "Date", render: (r) => r.date },
                {
                  key: "kind",
                  header: "Kind",
                  render: (r) => (
                    <Badge color={r.kind === "holiday" ? "blue" : "purple"}>
                      {r.kind === "holiday" ? "Closed Holiday" : "Restricted Holiday (RH)"}
                    </Badge>
                  ),
                },
                { key: "label", header: "Holiday Label", render: (r) => r.label || "—" },
              ]}
              empty={{
                icon: FaCog,
                title: "No holidays published",
                description: "Add institute closed holidays and restricted holidays here.",
              }}
            />
          </Card>
        </Tabs.Panel>

        {/* Tab 2: Vacations */}
        <Tabs.Panel value="vacations">
          <Card padding="lg">
            <Group justify="space-between" mb="md">
              <Text fw={600} size="sm">
                Academic Vacation Calendar (Faculty Vacation Leave eligibility window)
              </Text>
              <Button size="xs" color="teal" onClick={() => setOpenVacation(true)}>
                Add Vacation Period
              </Button>
            </Group>

            <DataTable<VacationPeriod>
              rows={vacationsData?.results ?? []}
              loading={vacPending}
              rowKey={(r) => r.id}
              columns={[
                { key: "name", header: "Period Name", render: (r) => <Text fw={600}>{r.name}</Text> },
                { key: "start", header: "From", render: (r) => r.start_date },
                { key: "end", header: "To", render: (r) => r.end_date },
                {
                  key: "active",
                  header: "Status",
                  render: (r) => (
                    <Badge color={r.is_active ? "green" : "gray"}>
                      {r.is_active ? "Active" : "Archived"}
                    </Badge>
                  ),
                },
              ]}
              empty={{
                icon: FaUmbrellaBeach,
                title: "No academic vacation periods registered",
                description: "Register summer/winter vacations for faculty VL entitlement.",
              }}
            />
          </Card>
        </Tabs.Panel>

        {/* Tab 3: Offline Leave */}
        <Tabs.Panel value="offline">
          <Card padding="lg">
            <Stack gap="md">
              <Text fw={600} size="sm">
                Retrospective Offline Sanction Synchronization (BR-EL-029, EL-UC-016)
              </Text>
              <Text size="xs" c="dimmed">
                Use this facility to record leaves sanctioned via offline paper files or emergency
                administrative approvals. Requires official sanction reference numbers.
              </Text>

              <Button
                color="indigo"
                style={{ alignSelf: "flex-start" }}
                onClick={() => setOpenOffline(true)}
              >
                Record Offline Sanctioned Leave
              </Button>
            </Stack>
          </Card>
        </Tabs.Panel>
      </Tabs>

      {/* Holiday Modal */}
      <Modal opened={openHoliday} onClose={() => setOpenHoliday(false)} title="Add Holiday">
        <Stack gap="sm">
          <DateInput label="Date" value={holidayDate} onChange={setHolidayDate} required />
          <Select
            label="Kind"
            value={holidayKind}
            onChange={setHolidayKind}
            data={[
              { value: "holiday", label: "Closed Holiday" },
              { value: "restricted", label: "Restricted Holiday (RH)" },
            ]}
            required
          />
          <TextInput
            label="Holiday Name / Label"
            placeholder="e.g. Republic Day, Diwali..."
            value={holidayLabel}
            onChange={(e) => setHolidayLabel(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <Button onClick={submitHoliday} loading={addHoliday.isPending}>
              Publish Holiday
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Vacation Modal */}
      <Modal
        opened={openVacation}
        onClose={() => setOpenVacation(false)}
        title="Add Academic Vacation Period"
      >
        <Stack gap="sm">
          <TextInput
            label="Vacation Name"
            placeholder="e.g. Summer Vacation 2026"
            value={vacationName}
            onChange={(e) => setVacationName(e.currentTarget.value)}
            required
          />
          <DateInput label="From Date" value={vacStart} onChange={setVacStart} required />
          <DateInput label="To Date" value={vacEnd} onChange={setVacEnd} required />
          <Group justify="flex-end">
            <Button color="teal" onClick={submitVacation} loading={addVacation.isPending}>
              Register Vacation
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Offline Leave Modal */}
      <Modal
        opened={openOffline}
        onClose={() => setOpenOffline(false)}
        title="Record Offline Sanctioned Leave"
        size="lg"
      >
        <Stack gap="sm">
          <SimpleGrid cols={2}>
            <NumberInput
              label="Employee User ID"
              placeholder="e.g. 101"
              value={offlineUserId}
              onChange={setOfflineUserId}
              required
            />
            <Select
              label="Employee Category"
              value={offlineKind}
              onChange={setOfflineKind}
              data={[
                { value: "faculty", label: "Faculty" },
                { value: "staff", label: "Staff" },
              ]}
              required
            />
          </SimpleGrid>

          <SimpleGrid cols={2}>
            <Select
              label="Leave Type"
              value={offlineCategory}
              onChange={setOfflineCategory}
              data={CATEGORY_OPTIONS}
              required
            />
            <TextInput
              label="Department"
              value={offlineDept}
              onChange={(e) => setOfflineDept(e.currentTarget.value)}
            />
          </SimpleGrid>

          <SimpleGrid cols={2}>
            <DateInput label="From Date" value={offlineStart} onChange={setOfflineStart} required />
            <DateInput label="To Date" value={offlineEnd} onChange={setOfflineEnd} required />
          </SimpleGrid>

          <TextInput
            label="Sanction Reference / File Number"
            placeholder="e.g. IIITDMJ/ESTT/LEAVE/2026/042"
            value={offlineSanctionRef}
            onChange={(e) => setOfflineSanctionRef(e.currentTarget.value)}
            required
          />

          <Textarea
            label="Purpose / Administrative Remarks"
            value={offlinePurpose}
            onChange={(e) => setOfflinePurpose(e.currentTarget.value)}
          />

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setOpenOffline(false)}>
              Cancel
            </Button>
            <Button color="indigo" onClick={submitOffline} loading={recordOffline.isPending}>
              Save Offline Sanction
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
