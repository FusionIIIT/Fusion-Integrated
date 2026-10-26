import {
  Button,
  Card,
  Grid,
  Group,
  Select,
  Stack,
  Switch,
  Text,
  TextInput,
  Textarea,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useState } from "react";
import { FaHistory, FaSyncAlt } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import {
  useAdjustBalance,
  useRecordOffline,
  useTriggerSLA,
  useTriggerYearEnd,
} from "../api/hooks";

export function LeaveAdminView() {
  const yearEndMutation = useTriggerYearEnd();
  const slaMutation = useTriggerSLA();
  const adjustMutation = useAdjustBalance();
  const offlineMutation = useRecordOffline();

  // Balance adjust form
  const [adjUserId, setAdjUserId] = useState<number | string>("");
  const [adjYear, setAdjYear] = useState<number>(new Date().getFullYear());
  const [adjType, setAdjType] = useState<string>("CL");
  const [adjDelta, setAdjDelta] = useState<number | string>(1);
  const [adjIsCredit, setAdjIsCredit] = useState<boolean>(true);

  // Offline record form
  const [offUserId, setOffUserId] = useState<number | string>("");
  const [offKind, setOffKind] = useState<string>("staff");
  const [offType, setOffType] = useState<string>("CL");
  const [offStart, setOffStart] = useState<string>("");
  const [offEnd, setOffEnd] = useState<string>("");
  const [offReason, setOffReason] = useState<string>("");
  const [offSanctionRef, setOffSanctionRef] = useState<string>("");
  const [offSanctionDate, setOffSanctionDate] = useState<string>("");
  const [offSanctionedBy, setOffSanctionedBy] = useState<string>("");

  const handleYearEnd = async () => {
    if (!window.confirm("Execute Year-End Processing? This lapses CL/RH and converts Faculty VL to EL.")) return;
    try {
      const res = await yearEndMutation.mutateAsync(new Date().getFullYear());
      notifications.show({
        title: "Year-End Processing Complete",
        message: `Processed ${res.employees_processed} employees. Converted ${res.total_vl_converted_to_el} VL to EL for Year ${res.next_year}.`,
        color: "green",
      });
    } catch (e) {
      notifications.show({ title: "Year-End Failed", message: errorMessage(e), color: "red" });
    }
  };

  const handleSLA = async () => {
    try {
      const res = await slaMutation.mutateAsync();
      notifications.show({
        title: "SLA Processing Complete",
        message: `Reminded ${res.reminded} tasks; Escalated ${res.escalated} tasks.`,
        color: "blue",
      });
    } catch (e) {
      notifications.show({ title: "SLA Check Failed", message: errorMessage(e), color: "red" });
    }
  };

  const handleAdjustSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!adjUserId) return;
    try {
      await adjustMutation.mutateAsync({
        user_id: Number(adjUserId),
        year: adjYear,
        leave_type: adjType,
        delta: Number(adjDelta),
        is_credit: adjIsCredit,
      });
      notifications.show({ title: "Balance Adjusted", message: "Leave balance successfully updated.", color: "green" });
    } catch (err) {
      notifications.show({ title: "Adjustment Failed", message: errorMessage(err), color: "red" });
    }
  };

  const handleOfflineSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!offUserId || !offStart || !offEnd || !offSanctionRef) return;
    try {
      await offlineMutation.mutateAsync({
        applicant_user_id: Number(offUserId),
        applicant_kind: offKind,
        leave_type: offType,
        start_date: offStart,
        end_date: offEnd,
        reason: offReason,
        sanction_ref: offSanctionRef,
        sanction_date: offSanctionDate || offStart,
        sanctioned_by: offSanctionedBy || "Registrar",
      });
      notifications.show({ title: "Offline Leave Synchronized", message: "Sanctioned leave record added and balance deducted.", color: "green" });
      setOffSanctionRef("");
      setOffReason("");
    } catch (err) {
      notifications.show({ title: "Offline Entry Failed", message: errorMessage(err), color: "red" });
    }
  };

  return (
    <Stack gap="xl">
      <Card withBorder padding="md" radius="md">
        <Title order={4} mb="xs">Institutional Event Triggers</Title>
        <Text size="sm" c="dimmed" mb="md">
          Execute automated institutional workflows adhering to BR-EL-007 (Year-End VL conversion) and BR-EL-032/033 (SLA checks).
        </Text>
        <Group>
          <Button color="indigo" leftSection={<FaSyncAlt />} onClick={handleYearEnd} loading={yearEndMutation.isPending}>
            Execute Year-End Processing
          </Button>
          <Button color="teal" variant="light" leftSection={<FaHistory />} onClick={handleSLA} loading={slaMutation.isPending}>
            Evaluate Task SLA Thresholds
          </Button>
        </Group>
      </Card>

      <Card withBorder padding="md" radius="md">
        <Title order={4} mb="md">Manual Leave Balance Adjustment (BR-EL-037)</Title>
        <form onSubmit={handleAdjustSubmit}>
          <Grid>
            <Grid.Col span={{ base: 12, sm: 4 }}>
              <TextInput label="User ID" required type="number" value={adjUserId} onChange={(e) => setAdjUserId(e.target.value)} />
            </Grid.Col>
            <Grid.Col span={{ base: 12, sm: 4 }}>
              <Select label="Leave Category" value={adjType} onChange={(v) => setAdjType(v || "CL")} data={["CL", "RH", "SCL", "EL", "COL", "VL"]} />
            </Grid.Col>
            <Grid.Col span={{ base: 12, sm: 4 }}>
              <TextInput label="Year" required type="number" value={adjYear} onChange={(e) => setAdjYear(Number(e.target.value))} />
            </Grid.Col>
            <Grid.Col span={{ base: 12, sm: 6 }}>
              <TextInput label="Days (Delta)" required type="number" step="0.5" value={adjDelta} onChange={(e) => setAdjDelta(e.target.value)} />
            </Grid.Col>
            <Grid.Col span={{ base: 12, sm: 6 }}>
              <Switch label={adjIsCredit ? "Credit Balance (+)" : "Deduct Balance (-)"} checked={adjIsCredit} onChange={(e) => setAdjIsCredit(e.currentTarget.checked)} mt="xl" />
            </Grid.Col>
          </Grid>
          <Group justify="flex-end" mt="md">
            <Button type="submit" loading={adjustMutation.isPending}>Apply Balance Adjustment</Button>
          </Group>
        </form>
      </Card>

      <Card withBorder padding="md" radius="md">
        <Title order={4} mb="md">Record Retrospective Offline Sanctioned Leave (EL-UC-016)</Title>
        <form onSubmit={handleOfflineSubmit}>
          <Grid>
            <Grid.Col span={{ base: 12, sm: 4 }}>
              <TextInput label="Applicant User ID" required type="number" value={offUserId} onChange={(e) => setOffUserId(e.target.value)} />
            </Grid.Col>
            <Grid.Col span={{ base: 12, sm: 4 }}>
              <Select label="Employee Kind" value={offKind} onChange={(v) => setOffKind(v || "staff")} data={[{ value: "staff", label: "Staff" }, { value: "faculty", label: "Faculty" }]} />
            </Grid.Col>
            <Grid.Col span={{ base: 12, sm: 4 }}>
              <Select label="Leave Category" value={offType} onChange={(v) => setOffType(v || "CL")} data={["CL", "RH", "SCL", "EL", "COL", "VL"]} />
            </Grid.Col>
            <Grid.Col span={{ base: 12, sm: 6 }}>
              <TextInput label="Start Date" required type="date" value={offStart} onChange={(e) => setOffStart(e.target.value)} />
            </Grid.Col>
            <Grid.Col span={{ base: 12, sm: 6 }}>
              <TextInput label="End Date" required type="date" value={offEnd} onChange={(e) => setOffEnd(e.target.value)} />
            </Grid.Col>
            <Grid.Col span={{ base: 12, sm: 4 }}>
              <TextInput label="Paper Sanction Ref" placeholder="e.g. ESTT/2026/012" required value={offSanctionRef} onChange={(e) => setOffSanctionRef(e.target.value)} />
            </Grid.Col>
            <Grid.Col span={{ base: 12, sm: 4 }}>
              <TextInput label="Sanction Date" type="date" value={offSanctionDate} onChange={(e) => setOffSanctionDate(e.target.value)} />
            </Grid.Col>
            <Grid.Col span={{ base: 12, sm: 4 }}>
              <TextInput label="Sanctioned By (Authority)" placeholder="e.g. Registrar" value={offSanctionedBy} onChange={(e) => setOffSanctionedBy(e.target.value)} />
            </Grid.Col>
            <Grid.Col span={12}>
              <Textarea label="Reason / Notes" value={offReason} onChange={(e) => setOffReason(e.target.value)} />
            </Grid.Col>
          </Grid>
          <Group justify="flex-end" mt="md">
            <Button type="submit" color="teal" loading={offlineMutation.isPending}>Record Offline Leave</Button>
          </Group>
        </form>
      </Card>
    </Stack>
  );
}
