import { useState } from "react";
import {
  Button,
  Card,
  Container,
  Group,
  NumberInput,
  Select,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  Textarea,
  Title,
  Alert,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaSyncAlt, FaFileSignature } from "react-icons/fa";

import { PageHeader } from "../../../ui/components/PageHeader";
import { elmApi } from "../api/elmApi";
import type { LeaveCategoryType } from "../types";

export default function AdminLeavePage() {
  // Offline leave state
  const [offlineUserId, setOfflineUserId] = useState<number | string>("");
  const [offlineCategory, setOfflineCategory] = useState<LeaveCategoryType>("CL");
  const [offlineStart, setOfflineStart] = useState("");
  const [offlineEnd, setOfflineEnd] = useState("");
  const [offlineRef, setOfflineRef] = useState("");
  const [sanctionAuthority, setSanctionAuthority] = useState("");
  const [sanctionDate, setSanctionDate] = useState("");
  const [offlineRemarks, setOfflineRemarks] = useState("");
  const [syncingOffline, setSyncingOffline] = useState(false);

  // Year end rollover state
  const [rolloverUserId, setRolloverUserId] = useState<number | string>("");
  const [rolloverYear, setRolloverYear] = useState<number | string>(new Date().getFullYear());
  const [runningRollover, setRunningRollover] = useState(false);
  const [rolloverResult, setRolloverResult] = useState<Record<string, unknown> | null>(null);

  const handleRecordOffline = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!offlineUserId || !offlineStart || !offlineEnd || !offlineRef || !sanctionAuthority) {
      notifications.show({
        title: "Validation Error",
        message: "Please fill in all required offline leave fields.",
        color: "red",
      });
      return;
    }

    setSyncingOffline(true);
    try {
      const res = await elmApi.recordOfflineLeave({
        user_id: Number(offlineUserId),
        category: offlineCategory,
        start_date: offlineStart,
        end_date: offlineEnd,
        offline_reference_no: offlineRef,
        sanctioning_authority_name: sanctionAuthority,
        sanction_date: sanctionDate || offlineStart,
        remarks: offlineRemarks,
      });

      notifications.show({
        title: "Success",
        message: `${res.message} (Reference #${res.offline_reference_no})`,
        color: "green",
      });

      // Clear fields
      setOfflineRef("");
      setOfflineRemarks("");
    } catch (err: unknown) {
      notifications.show({
        title: "Error",
        message: err instanceof Error ? err.message : "Failed to record offline leave.",
        color: "red",
      });
    } finally {
      setSyncingOffline(false);
    }
  };

  const handleRunRollover = async () => {
    if (!rolloverUserId) {
      notifications.show({
        title: "Validation Error",
        message: "Employee User ID is required for rollover.",
        color: "red",
      });
      return;
    }

    setRunningRollover(true);
    setRolloverResult(null);
    try {
      const res = await elmApi.runYearEndRollover(
        Number(rolloverUserId),
        Number(rolloverYear)
      );
      setRolloverResult(res);
      notifications.show({
        title: "Rollover Completed",
        message: `Year-end rollover executed for User #${rolloverUserId}.`,
        color: "green",
      });
    } catch (err: unknown) {
      notifications.show({
        title: "Rollover Failed",
        message: err instanceof Error ? err.message : "Failed to run year-end rollover.",
        color: "red",
      });
    } finally {
      setRunningRollover(false);
    }
  };

  return (
    <Container size="xl" py="lg">
      <PageHeader
        title="Leave Administration & Offline Synchronization"
        subtitle="Record authorized offline-sanctioned leave and execute annual boundary rollovers."
      />

      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg">
        {/* Offline Leave Synchronization */}
        <Card withBorder radius="md">
          <Group mb="xs">
            <FaFileSignature size={20} color="#1c7ed6" />
            <Title order={4}>Retrospective Offline Leave Synchronization</Title>
          </Group>
          <Text size="xs" c="dimmed" mb="md">
            (BR-EL-029, UC-EL-016: Synchronizes leave already authorized through an offline/paper
            route due to emergencies or outages, directly updating balances without a second approval workflow.)
          </Text>

          <form onSubmit={handleRecordOffline}>
            <Stack gap="sm">
              <NumberInput
                label="Employee IAM User ID"
                placeholder="e.g. 102"
                required
                value={offlineUserId}
                onChange={(v) => setOfflineUserId(v)}
                min={1}
              />

              <Select
                label="Leave Category"
                required
                data={["CL", "RH", "SCL", "EL", "COL", "VL"]}
                value={offlineCategory}
                onChange={(v) => setOfflineCategory((v as LeaveCategoryType) || "CL")}
              />

              <Group grow>
                <TextInput
                  type="date"
                  label="Start Date"
                  required
                  value={offlineStart}
                  onChange={(e) => setOfflineStart(e.currentTarget.value)}
                />
                <TextInput
                  type="date"
                  label="End Date"
                  required
                  value={offlineEnd}
                  onChange={(e) => setOfflineEnd(e.currentTarget.value)}
                />
              </Group>

              <TextInput
                label="Offline Sanction Order / File Reference No"
                placeholder="e.g. EST/2026/LV/892"
                required
                value={offlineRef}
                onChange={(e) => setOfflineRef(e.currentTarget.value)}
              />

              <TextInput
                label="Sanctioning Authority Name / Designation"
                placeholder="e.g. Director / Dean Faculty"
                required
                value={sanctionAuthority}
                onChange={(e) => setSanctionAuthority(e.currentTarget.value)}
              />

              <TextInput
                type="date"
                label="Sanction Order Date"
                required
                value={sanctionDate}
                onChange={(e) => setSanctionDate(e.currentTarget.value)}
              />

              <Textarea
                label="Remarks / Notes"
                placeholder="Reference details or background context"
                value={offlineRemarks}
                onChange={(e) => setOfflineRemarks(e.currentTarget.value)}
              />

              <Button type="submit" loading={syncingOffline} mt="sm">
                Record Offline Sanctioned Leave
              </Button>
            </Stack>
          </form>
        </Card>

        {/* Year-End Rollover */}
        <Card withBorder radius="md">
          <Group mb="xs">
            <FaSyncAlt size={20} color="#1c7ed6" />
            <Title order={4}>Event-Triggered Year-End Rollover</Title>
          </Group>
          <Text size="xs" c="dimmed" mb="md">
            (BR-EL-002..009, UC-EL-020: Lapses unused CL/RH/SCL, converts unused faculty VL to EL
            at 2 VL : 1 EL, and carries forward EL and COL balances into the next year.)
          </Text>

          <Stack gap="sm">
            <NumberInput
              label="Target Employee User ID"
              placeholder="e.g. 101"
              required
              value={rolloverUserId}
              onChange={(v) => setRolloverUserId(v)}
              min={1}
            />

            <NumberInput
              label="Boundary Year (Ending Year)"
              placeholder="e.g. 2026"
              required
              value={rolloverYear}
              onChange={(v) => setRolloverYear(v)}
              min={2020}
            />

            <Button
              color="teal"
              loading={runningRollover}
              leftSection={<FaSyncAlt />}
              onClick={handleRunRollover}
              mt="sm"
            >
              Trigger Year-End Processing
            </Button>

            {rolloverResult && (
              <Alert color="teal" title="Processing Completed" mt="md">
                <Text size="sm">
                  <strong>Converted VL to EL:</strong> {String(rolloverResult.converted_el_from_vl)} days
                </Text>
                <Text size="sm">
                  <strong>Carried Forward EL:</strong> {String(rolloverResult.carried_forward_el)} days
                </Text>
                <Text size="sm">
                  <strong>Carried Forward COL:</strong> {String(rolloverResult.carried_forward_col)} days
                </Text>
              </Alert>
            )}
          </Stack>
        </Card>
      </SimpleGrid>
    </Container>
  );
}
