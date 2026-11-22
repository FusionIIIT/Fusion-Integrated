import { useEffect, useState } from "react";
import { Card, Container, SimpleGrid, Text } from "@mantine/core";
import { http } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";

type Report = { total: number; by_status: { status: string; count: number }[] };
export default function ReportsPage() {
  const [data, setData] = useState<Report>();
  const [error, setError] = useState<unknown>();
  useEffect(() => { http.get<Report>("/pms/reports").then((r) => setData(r.data)).catch(setError); }, []);
  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;
  return <Container size="xl"><PageHeader title="PMS Reports" subtitle="Application status totals in your authorized scope." />
    <SimpleGrid cols={{ base: 1, sm: 3 }}>
      <Card withBorder><Text c="dimmed">Applications</Text><Text size="xl" fw={700}>{data?.total ?? "—"}</Text></Card>
      {(data?.by_status ?? []).map((row) => <Card withBorder key={row.status}><Text c="dimmed">{row.status.replaceAll("_", " ")}</Text><Text size="xl" fw={700}>{row.count}</Text></Card>)}
    </SimpleGrid>
  </Container>;
}
