import { useState } from "react";
import {
  Alert, Button, Card, Container, Grid, Group, NumberInput, Select, Stack,
  Switch, Text, Textarea, TextInput,
} from "@mantine/core";
import { DateInput } from "@mantine/dates";
import { notifications } from "@mantine/notifications";
import { useNavigate } from "react-router-dom";

import { errorMessage } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useApply, useMyBalances } from "../api/hooks";
import type { Category, Half } from "../api/types";

const CATEGORIES: { value: Category; label: string }[] = [
  { value: "CL", label: "Casual Leave" },
  { value: "RH", label: "Restricted Holiday" },
  { value: "SCL", label: "Special Casual Leave" },
  { value: "EL", label: "Earned Leave" },
  { value: "COL", label: "Commuted Leave" },
  { value: "VL", label: "Vacation Leave" },
];

/** BR-EL-010: only casual leave is taken in halves. */
const HALF_DAY = new Set<Category>(["CL"]);
/** BR-EL-001. A single named date, chosen from the published calendar. */
const SINGLE_DAY = new Set<Category>(["RH"]);

function iso(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export default function ApplyPage() {
  const navigate = useNavigate();
  const apply = useApply();
  const balances = useMyBalances();

  const [category, setCategory] = useState<Category>("CL");
  const [from, setFrom] = useState<Date | null>(null);
  const [to, setTo] = useState<Date | null>(null);
  const [half, setHalf] = useState<Half | null>(null);
  const [reason, setReason] = useState("");
  const [substitute, setSubstitute] = useState<number | "">("");
  const [station, setStation] = useState(false);
  const [destination, setDestination] = useState("");

  const single = SINGLE_DAY.has(category);
  const end = single ? from : to;
  const oneDay = Boolean(from && end && iso(from) === iso(end));
  const canTakeHalfDay = HALF_DAY.has(category) && oneDay;
  const available = balances.data?.find((b) => b.category === category)?.available;
  const incomplete = !from || !end || reason.trim().length < 5;

  function submit() {
    if (!from || !end) return;
    apply.mutateAsync({
      category,
      starts_on: iso(from),
      ends_on: iso(end),
      reason: reason.trim(),
      // Cleared, not just hidden: a stale half-day on a multi-day request is refused.
      half: canTakeHalfDay ? half : null,
      substitute_user_id: substitute === "" ? null : Number(substitute),
      station: station && destination.trim()
        ? { destination: destination.trim(), from_date: iso(from), to_date: iso(end) }
        : null,
    })
      .then(() => {
        notifications.show({
          color: "green", title: "Submitted",
          message: "Your request has entered the approval workflow.",
        });
        navigate("..");
      })
      .catch((e) => notifications.show({
        color: "red", title: "Not submitted", message: errorMessage(e),
      }));
  }

  return (
    <Container size="md">
      <PageHeader
        title="Apply for Leave"
        subtitle="Checked against the policy and calendar in force on the dates you choose"
      />
      <Card padding="lg">
        <Stack gap="md">
          <Grid>
            <Grid.Col span={{ base: 12, sm: 6 }}>
              <Select
                label="Leave type" data={CATEGORIES} value={category}
                allowDeselect={false}
                onChange={(v) => { setCategory(v as Category); setHalf(null); }}
              />
            </Grid.Col>
            <Grid.Col span={{ base: 12, sm: 6 }}>
              <Text size="xs" c="dimmed" mt={28}>
                {available != null
                  ? `${available} day(s) available in ${category}`
                  : "Balance loading"}
              </Text>
            </Grid.Col>
          </Grid>

          <Grid>
            <Grid.Col span={{ base: 12, sm: 6 }}>
              <DateInput
                label={single ? "Date" : "From"} value={from} onChange={setFrom}
              />
            </Grid.Col>
            {!single && (
              <Grid.Col span={{ base: 12, sm: 6 }}>
                <DateInput label="To" value={to} onChange={setTo} minDate={from ?? undefined} />
              </Grid.Col>
            )}
          </Grid>

          {canTakeHalfDay && (
            <Select
              label="Half day (optional)" clearable value={half}
              onChange={(v) => setHalf(v as Half | null)}
              data={[
                { value: "FIRST", label: "First half" },
                { value: "SECOND", label: "Second half" },
              ]}
            />
          )}

          {category === "RH" && (
            <Alert color="blue" variant="light">
              A restricted holiday must be one of the dates published in this
              year&apos;s calendar.
            </Alert>
          )}
          {category === "VL" && (
            <Alert color="blue" variant="light">
              Vacation leave must fall inside a published vacation period.
            </Alert>
          )}

          <Textarea
            label="Reason" autosize minRows={3} value={reason}
            onChange={(e) => setReason(e.currentTarget.value)}
          />

          <NumberInput
            label="Substitute employee ID (where one is required)"
            description="The person who will hold your responsibilities. They are asked to consent before the request moves on."
            value={substitute} min={1} allowDecimal={false}
            onChange={(v) => setSubstitute(v === "" ? "" : Number(v))}
          />

          <Switch
            label="I will be away from headquarters"
            checked={station} onChange={(e) => setStation(e.currentTarget.checked)}
          />
          {station && (
            <TextInput
              label="Destination" value={destination}
              onChange={(e) => setDestination(e.currentTarget.value)}
            />
          )}

          <Group justify="flex-end">
            <Button variant="subtle" color="gray" onClick={() => navigate("..")}>
              Cancel
            </Button>
            <Button
              onClick={submit} loading={apply.isPending} disabled={incomplete}
            >
              Submit
            </Button>
          </Group>
          {incomplete && (
            <Text size="xs" c="dimmed" ta="right">
              Choose the dates and state a reason before submitting.
            </Text>
          )}
        </Stack>
      </Card>
    </Container>
  );
}
