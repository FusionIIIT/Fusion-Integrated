import {
  Alert, Button, Card, Checkbox, Container, Group, List, SegmentedControl, Select, SimpleGrid,
  Stack, Text, TextInput, Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import dayjs from "dayjs";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useApply, useEffectiveCalendar, useOverview } from "../api/hooks";
import type { Category, Half } from "../api/types";
import { LeaveDate, SubstitutePicker } from "../components/fields";

/** EL-UC-001: one application, Station Leave inside it; the server is the validator. */
export default function ApplyPage() {
  const navigate = useNavigate();
  const overview = useOverview();
  const apply = useApply();
  const [category, setCategory] = useState<Category | null>(null);
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [half, setHalf] = useState<Half>("");
  const [purpose, setPurpose] = useState("");
  const [station, setStation] = useState(false);
  const [stationFrom, setStationFrom] = useState("");
  const [stationTo, setStationTo] = useState("");
  const [address, setAddress] = useState("");
  const [evidence, setEvidence] = useState("");
  const [substitute, setSubstitute] = useState<number | null>(null);
  const year = start ? dayjs(start).year() : dayjs().year();
  const calendar = useEffectiveCalendar(year);

  const option = overview.data?.categories.find((c) => c.category === category);
  const balance = overview.data?.balances.find((b) => b.category === category);
  const restricted = useMemo(() => (calendar.data?.holidays ?? [])
    .filter((h) => h.kind === "restricted"), [calendar.data]);

  if (overview.error) return <Container><ErrorState error={overview.error} /></Container>;
  if (overview.data && !overview.data.configured) {
    return (
      <Container>
        <PageHeader title="Apply for Leave" />
        <Alert color="yellow" title="Leave is not set up yet">
          The leave policy has not been configured, so applications cannot be taken yet.
        </Alert>
      </Container>);
  }

  function submit() {
    if (!category) return;
    apply.mutate({
      category, start_date: start, end_date: half ? start : end || start, half, purpose,
      station_leave: station, station_from: station ? stationFrom || null : null,
      station_to: station ? stationTo || null : null, station_address: station ? address : "",
      evidence_reference: evidence, substitute_user_id: substitute,
    }, {
      onSuccess: (r) => {
        notifications.show({ color: "green", title: "Submitted",
          message: `Request #${r.id} is ${r.status_label.toLowerCase()}.` });
        navigate("/leave/mine");
      },
    });
  }

  const details = (apply.error as { response?: { data?: { error?: {
    details?: { message: string }[] } } } } | null)?.response?.data?.error?.details ?? [];

  return (
    <Container size="md">
      <PageHeader title="Apply for Leave"
        subtitle="Your request is checked against your balance, the calendar and your other leave" />
      <Card padding="lg">
        <Stack>
          <Select label="Leave category" required placeholder="Choose"
            data={(overview.data?.categories ?? []).map((c) => ({
              value: c.category, label: `${c.label} (${c.category})` }))}
            value={category} onChange={(v) => { setCategory(v as Category | null); setHalf(""); }} />
          {balance && <Text size="sm" c="dimmed">
            {Number(balance.available)} day(s) available ({Number(balance.balance)} held,
            {" "}{Number(balance.pending)} in pending requests).</Text>}
          {category === "RH" && (
            <Alert variant="light" color="blue" title="Restricted Holidays this year">
              {restricted.length ? restricted.map((h) => `${dayjs(h.date).format("DD MMM")} ${h.name}`)
                .join(" · ") : "None are published for this year."}
            </Alert>)}
          {category === "VL" && (
            <Alert variant="light" color="blue" title="Vacation periods">
              {(calendar.data?.vacations ?? []).map((v) =>
                `${v.label}: ${dayjs(v.start_date).format("DD MMM")} – ${dayjs(v.end_date).format("DD MMM")}`)
                .join(" · ") || "No vacation periods are recorded for this year."}
            </Alert>)}
          {option?.half_day && (
            <SegmentedControl value={half || "full"} onChange={(v) => setHalf(v === "full" ? "" : v as Half)}
              data={[{ value: "full", label: "Full day(s)" }, { value: "first", label: "First half" },
                { value: "second", label: "Second half" }]} />)}
          <SimpleGrid cols={{ base: 1, sm: 2 }}>
            <LeaveDate label={half ? "Date" : "From"} value={start} onChange={setStart} required />
            {!half && <LeaveDate label="To" value={end} onChange={setEnd} minDate={start} required />}
          </SimpleGrid>
          <Textarea label="Purpose" required value={purpose} autosize minRows={2}
            onChange={(e) => setPurpose(e.currentTarget.value)} />
          {option && option.substitute !== "none" && (
            <SubstitutePicker value={substitute} onChange={setSubstitute}
              required={option.substitute === "required"}
              label={option.substitute === "required" ? "Substitute" : "Substitute (if your duties need cover)"} />)}
          {option?.evidence_min_days && (
            <TextInput label="Medical evidence reference" value={evidence}
              description={`Required for ${Number(option.evidence_min_days)} day(s) or more`}
              onChange={(e) => setEvidence(e.currentTarget.value)} />)}
          <Checkbox label="I will be away from Jabalpur (Station Leave)" checked={station}
            onChange={(e) => setStation(e.currentTarget.checked)} />
          {station && (
            <SimpleGrid cols={{ base: 1, sm: 2 }}>
              <LeaveDate label="Leaving Jabalpur" value={stationFrom} onChange={setStationFrom} required />
              <LeaveDate label="Returning" value={stationTo} onChange={setStationTo} minDate={stationFrom} required />
              <TextInput label="Address while away" required value={address}
                onChange={(e) => setAddress(e.currentTarget.value)} />
            </SimpleGrid>)}
          {apply.error != null && (
            <Alert color="red" title="Not submitted">
              {details.length > 1 ? <List size="sm">{details.map((d) =>
                <List.Item key={d.message}>{d.message}</List.Item>)}</List> : errorMessage(apply.error)}
            </Alert>)}
          <Group justify="flex-end">
            <Button onClick={submit} loading={apply.isPending}
              disabled={!category || !start || (!half && !end) || !purpose.trim()}>
              Submit application</Button>
          </Group>
        </Stack>
      </Card>
    </Container>
  );
}
