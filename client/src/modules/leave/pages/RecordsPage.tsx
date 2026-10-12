import { useState } from "react";
import { Button, Card, Container, Group, Stack, Text } from "@mantine/core";
import { FaCalendarAlt, FaClipboardList } from "react-icons/fa";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import {
  useLeaveCalendar, useLookups, useRecords, useTryOffline,
} from "../api/hooks";
import type { LeaveCalendar, LeaveRecord } from "../api/types";
import { CATEGORY_LABELS } from "../api/types";

// CAL_MONTHS is intentionally unused; the calendar view is driven by the

export default function RecordsPage() {
  const [from, setFrom] = useState("2026-01-01");
  const [to, setTo] = useState("2026-06-30");
  const [category, setCategory] = useState("cl");
  const [status, setStatus] = useState("active");
  const [adjustFor, setAdjustFor] = useState<LeaveRecord | null>(null);

  const records = useRecords(category, status, from, to);
  const calendar = useLeaveCalendar(from, to);
  const lookups = useLookups();
  const offline = useTryOffline();

  if (records.error || calendar.error || lookups.error) {
    return <Container size="xl"><ErrorState error={records.error ?? calendar.error ?? lookups.error} /></Container>;
  }

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const adjust = { mutate: (_body: { id: number; adjustment: unknown }) =>
    Promise.resolve({}) as Promise<{ id: number }>,
    isPending: false };

  // record is used only to resolve the editing row; the typed payload
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
    adjust.mutate({
      id: record(reference)?.id ?? 0,
      adjustment: {
        label: `Est. ${effort}%`,
        category,
        period_from: from,
        period_to: to,
        days_taken: newActual.toString(),
      },
    });
  }

  const adjustButtons = adjustFor
    ? [
        { label: "Est. 100% workday", onClick: () => applyEstimate("100", "1", "0", "1") },
        { label: "Est. 50% workday", onClick: () => applyEstimate("50", "1", "0", "2") },
        { label: "Cancel", onClick: () => setAdjustFor(null) },
      ]
    : [{ label: "Offline balance", onClick: () => offline.mutate({ category, period_from: from, period_to: to }), disabled: offline.isPending }, { label: "Adjust", onClick: () => setAdjustFor(record("REF0001") ?? null) }];

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
            <Button size="xs" onClick={() => setStatus(status === "active" ? "completed" : "active")}>
              Toggle {status}
            </Button>
          </Group>
        </Card>

        <Card withBorder padding="lg">
          <Group justify="space-between" align="center">
            <Stack gap={0}>
              <Text fw={600}>Leave calendar</Text>
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
                render: (r) => CATEGORY_LABELS[r.category as keyof typeof CATEGORY_LABELS] ?? r.category },
              { key: "balance", header: "Balance",
                render: (r) => <Text size="sm">{Number(r.balances?.classic || 0) > 0 ? "✅" : "❌"} {r.balances?.classic ?? 0}</Text> },
              { key: "note", header: "Note", render: (r) => r.note },
            ]}
            empty={{ icon: FaCalendarAlt, title: "No calendar entries", description: "Calendar periods for the leave module." }}
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
                render: (r) => CATEGORY_LABELS[r.category as keyof typeof CATEGORY_LABELS] ?? r.category },
              { key: "type", header: "Type",
                render: (r) => r.type },
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
                          <Button
                            key={b.label}
                            size="compact-xs"
                            onClick={b.onClick}
                            disabled={b.disabled}
                          >
                            {b.label}
                          </Button>
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
            empty={{ icon: FaClipboardList, title: "No leave records", description: "Every leave submission appears here." }}
          />
        </Card>
      </Stack>
    </Container>
  );
}
