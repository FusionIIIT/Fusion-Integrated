import { useCallback, useEffect, useState } from "react";
import { Alert, Button, Card, Container, Group, Stack, Text, Title } from "@mantine/core";
import { NavLink } from "react-router-dom";
import { errorMessage, http } from "../../../lib/http";
import type { Application, Page } from "../api";

type Task = "mine" | "substitute" | "unit-head" | "sanction";
type Action = { label: string; path: string; body: Record<string, unknown> };

function actions(row: Application): Action[] {
  if (row.allowed_actions.includes("substitute-response")) {
    return [
      { label: "Accept", path: "substitute-response", body: { accept: true } },
      { label: "Decline", path: "substitute-response", body: { accept: false } },
    ];
  }
  if (row.allowed_actions.includes("unit-head-review")) {
    const decisions = ["CL", "RH"].includes(row.category)
      ? ["Approve", "Reject"] : ["Recommended", "Not Recommended"];
    return decisions.map(decision => ({
      label: decision, path: "unit-head-review", body: { decision },
    }));
  }
  if (row.allowed_actions.includes("establishment-route")) {
    return [{ label: "Verify and route", path: "establishment-route", body: {} }];
  }
  const path = row.allowed_actions.find(value => ["final-decision", "director-decision"].includes(value));
  return path ? ["Approve", "Reject"].map(decision => ({
    label: decision, path, body: { decision },
  })) : [];
}

export function ElmNavigation() {
  return <Group component="nav" aria-label="Leave navigation" mb="lg">
    <NavLink to="../apply">Apply</NavLink>
    <NavLink to="../my-leaves">My applications</NavLink>
    <NavLink to="../substitute-requests">Substitute requests</NavLink>
    <NavLink to="../unit-head-review">Unit Head review</NavLink>
    <NavLink to="../sanction">Sanctioning</NavLink>
  </Group>;
}

export default function RequestsPage({ title, task }: { title: string; task: Task }) {
  const first = `/elm/applications/?task=${task}`;
  const [url, setUrl] = useState(first);
  const [page, setPage] = useState<Page<Application> | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await http.get<Page<Application>>(url);
      setPage(response.data);
    } catch (failure) {
      setError(errorMessage(failure));
    } finally {
      setLoading(false);
    }
  }, [url]);
  useEffect(() => { void load(); }, [load]);

  async function act(row: Application, action: Action) {
    setBusy(row.id);
    setError("");
    try {
      await http.post(`/elm/applications/${row.id}/${action.path}/`, action.body);
      await load();
    } catch (failure) {
      setError(errorMessage(failure));
    } finally {
      setBusy(null);
    }
  }

  return <Container size="lg">
    <ElmNavigation />
    <Title order={1} mb="lg">{title}</Title>
    {error && <Alert role="alert" color="red" mb="md">{error}</Alert>}
    {loading && <Text role="status">Loading requests…</Text>}
    {!loading && page?.results.length === 0 && <Text>No requests.</Text>}
    <Stack>
      {page?.results.map(row => <Card key={row.id} withBorder>
        <Title order={2} size="h3">{row.category}: {row.start_date}–{row.end_date}</Title>
        <Text>{row.num_days} days — {row.state}</Text>
        {row.unit_head_recommendation && <Text>Unit Head: {row.unit_head_recommendation}</Text>}
        {row.remarks && <Text>Purpose / remarks: {row.remarks}</Text>}
        {Object.keys(row.station_leave_details ?? {}).length > 0 &&
          <Text>Station Leave: {JSON.stringify(row.station_leave_details)}</Text>}
        {task !== "mine" && <Group mt="md">
          {actions(row).map(action => <Button
            key={action.label} disabled={busy !== null || loading}
            loading={busy === row.id} onClick={() => void act(row, action)}
          >{action.label}</Button>)}
        </Group>}
      </Card>)}
    </Stack>
    {page && <Group mt="lg">
      <Button variant="default" disabled={!page.previous || loading}
        onClick={() => { if (page.previous) setUrl(page.previous); }}>Previous</Button>
      <Text>{page.count} requests</Text>
      <Button variant="default" disabled={!page.next || loading}
        onClick={() => { if (page.next) setUrl(page.next); }}>Next</Button>
    </Group>}
  </Container>;
}
