import { useState } from "react";
import { Button, Card, Container, Group, Stack, Tabs, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCalendarAlt, FaFileCircle, FaLock, FaTicketAlt } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import {
  useAdjustments, useLeaveCalendar, useLookups, useRecords, useTryOffline,
} from "../api/hooks";
import type { Adjustment, LeaveCalendar, Lookup, LeaveRecord } from "../api/types";
import { CATEGORY_LABELS, LEAVE_TYPES } from "../api/types";

const CAL_MONTHS = 6;

export default function RecordsPage() {
  const [from, setFrom] = useState("2026-01-01");
  const [to, setTo] = useState("2026-06-30");
  const [category, setCategory] = useState("cl");
  const [status, setStatus] = useState("active");
  const [value, setValue] = useState<number | null>(null);
  const [adjustFor, setAdjustFor] = useState<LeaveRecord | null>(null);
  const [adjustNote, setAdjustNote] = useState("");

  const records = useRecords(category, status, from, to, null);
  const calendar = useLeaveCalendar(from, to);
  const lookups = useLookups();
  const offline = useTryOffline();
  const adjust = useAdjustments();

  if (records.error || calendar.error || lookups.error) {
    return <Container size="xl"><ErrorState error={records.error ?? calendar.error ?? lookups.error} /></Container>;
  }

  function record(reference: string): LeaveRecord | undefined {
    return (records.data?.results ?? []).find((r) =>
      r.reference === reference || r.request_id === reference || r.id === Number(reference));
  }

  function applyEstimate(effort: string, remaining: string, balance: string, days: string) {
    const pct = Math.min(1, Math.max(0, Number(effort) / 100));
    const remainingDays = Number(remaining) || 0;
    if (!Number.isFinite(pct) || !Number.isFinite(remainingDays)) return;
    const actual = Number(days) || 0;
    const newActual = Math.round(actual - remainingDays * (1 - pct));
    const newBalance = Math.max(0, Number(balance) - newActual);
    const adjusted = {
      category, period_from: from, period_to: to, days_taken: newActual,
      prorated_end_date: `2026-01-01`, note: `Estimated at ${effort}% workload`,
      method: "adjustment", proposal: "schedule-adjustment",
    } as Adjustment;
    adjust.mutate({ id: record(reference)?.id ?? 0, adjustment: adjusted });
  }

  const adjustButtons = adjustFor
    ? [
        { label: "Est. 100% workday", onClick: () => applyEstimate("100", "1", "0", "1") },
        { label: "Est. 50% workday", onClick: () => applyEstimate("50", "1", "0", "2") },
        { label: "Cancel", onClick: () => setAdjustFor(null) },
      ]
    : [{ label: "Offline balance", onClick: () => offline.mutate({ category, period_from: from, period_to: to }), disabled: offline.isPending }, { label: "Adjust", onClick: () => setAdjustFor(record("REF0001") ?? null) }];
  const lookupPrefix = (lookups.data?.lookup_categories ?? []).map((c) => c.value).join(" ");

  return (
    <Container size="xl">
      <PageHeader
        title="Leave Records"
        subtitle="Balance, calendar and every submission"
        action={
          <Group gap="xs">
            <Button variant="default" size="xs" onClick={() => setFrom("2026-01-01")}>
              {from}
            </Button>
            <Button variant="default" size="xs" onClick={() => setTo("2026-06-30")}>
              {to}
            </Button>
          </Group>
        }
      />

      <Stack gap="sm">
        <Card withBorder padding="md">
          <Group gap="md" wrap="wrap">
            <Stack gap={0}>
              <Text size="xs" c="dimmed">From</Text>
              <input type="date" value={from} onChange={(e) => setFrom(e.target.value)}
                     style={{ width: 140, padding: "4px 6px" }} />
            </Stack>
            <Stack gap={0}>
              <Text size="xs" c="dimmed">To</Text>
              <input type="date" value={to} onChange={(e) => setTo(e.target.value)}
                     style={{ width: 140, padding: "4px 6px" }} />
            </Stack>
            <Stack gap={0}>
              <Text size="xs" c="dimmed">Category</Text>
              <select value={category} onChange={(e) => setCategory(e.target.value)}
                      style={{ width: 160, padding: "4px 6px" }}>
                {(lookups.data?.lookup_categories ?? []).map((c) =>
                  <option key={c.value} value={c.value}>{c.label}</option>)}
              </select>
            </Stack>
            <Stack gap={0}>
              <Text size="xs" c="dimmed">Status</Text>
              <select value={status} onChange={(e) => setStatus(e.target.value)}
                      style={{ width: 160, padding: "4px 6px" }}>
                {["active", "withdrawn", "completed"].map((s) =>
                  <option key={s} value={s}>{s}</option>)}
              </select>
            </Stack>
            <input type="date" value={from} onChange={(e) => setFrom(e.target.value)}
                   style={{ width: 140, padding: "4px 6px" }} />
            <Button size="xs" onClick={() => setStatus(status === "active" ? "completed" : "active")}>
              Toggle {status}
            </Button>
          </Group>
        </Card>

        <Card withBorder padding="lg">
          <Group justify="space-between" align="center">
            <Stack gap={0}>
              <Text fw={600}>{CALENDAR_TITLE}</Text>
              <Text size="sm" c="dimmed">Calendar of {from} → {to}</Text>
            </Stack>
            <Button size="xs" variant="light" color="gray">Export</Button>
          </Group>
          <DataTable<LeaveCalendar>
            rows={calendar.data?.results ?? []}
            loading={calendar.isPending}
            rowKey={(r) => `${r.period_from}-${r.period_to}`}
            minWidth={640}
            columns={[
              { key: "period", header: "Period",
                render: (r) => <Text size="sm">
                  {r.period_from} → {r.period_to}</Text> },
              { key: "category", header: "Category",
                render: (r) => CATEGORY_LABELS[r.category] ?? r.category },
              { key: "balance", header: "Balance",
                render: (r) => <Text size="sm">{Number(r.balances?.classic || 0) > 0 ? "✅" : "❌"} {r.balances?.classic ?? 0}</Text> },
              { key: "note", header: "Note", render: (r) => r.note },
            ]}
          />
        </Card>

        <Card withBorder padding="lg">
          <Group justify="space-between" align="center">
            <Stack gap={0}>
              <Text fw={600}>Leave records</Text>
              <Text size="sm" c="dimmed">
                Pending: {records.data?.results.filter((r) => r.status === "pending").length ?? 0}
              </Text>
            </Stack>
            <Button size="xs" variant="light" color="gray">Export</Button>
          </Group>
          <DataTable<LeaveRecord>
            rows={records.data?.results ?? []}
            loading={records.isPending}
            rowKey={(r) => r.id}
            minWidth={1000}
            columns={[
              { key: "reference", header: "Reference",
                render: (r) => <Text size="sm">{r.reference ?? `#${r.request_id}`}</Text> },
              { key: "category", header: "Category",
                render: (r) => CATEGORY_LABELS[r.category] ?? r.category },
              { key: "type", header: "Type",
                render: (r) => LEAVE_TYPES[r.type] ?? r.type },
              {
                key: "periods", header: "Periods",
                render: (r) => (
                  <Text size="sm">{r.period_from} → {r.period_to}</Text>
                ) },
              { key: "status", header: "Status", render: (r) => <StatusBadge status={r.status} /> },
              { key: "days", header: "Days", render: (r) => r.days_taken ?? 0 },
              {
                key: "actions", header: "", align: "right",
                render: (r) => (
                  <Group gap={4}>
                    {adjustFor?.id === r.id ? (
                      <Group gap={4}>
                        {adjustButtons.map((b) => (
                          <Button key={b.label} size="compact-xs" {...b.props}>{b.label}</Button>
                        ))}
                      </Group>
                    ) : (
                      <Button size="compact-xs" variant="light" onClick={() => setAdjustFor(r)}>
                        Estimate
                      </Button>
                    )}
                  </Group>
                ),
              },
            ]}
          />
        </Card>
      </Stack>
    </Container>
  );
}

const CALENDAR_TITLE = "Leave calendar";
