import { useEffect, useState } from "react";
import { Button, Card, Container, Group, Table, Text } from "@mantine/core";
import { Link, useNavigate } from "react-router-dom";

import { http } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useAuth } from "../../../auth/AuthProvider";

type PmsApplication = {
  id: string; application_number: string; title: string; status: string;
  technical_domain: string; created_at: string;
};

export default function ApplicationsPage() {
  const [rows, setRows] = useState<PmsApplication[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>();
  const navigate = useNavigate();
  const { session } = useAuth();
  const canCreate = session?.permissions.includes("pms.application.create") ?? false;
  const canReport = session?.permissions.includes("pms.report.view") ?? false;

  useEffect(() => {
    let active = true;
    http.get<PmsApplication[]>("/pms/applications")
      .then(({ data }) => { if (active) setRows(data); })
      .catch((e: unknown) => { if (active) setError(e); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;
  return (
    <Container size="xl">
      <PageHeader title="Patent Applications"
        subtitle="Create a draft, complete inventor and document records, then submit it for review."
        action={<Group>
          {canReport && <Button component={Link} to="/pms/reports" variant="light">Reports</Button>}
          {canCreate && <Button onClick={() => navigate("/pms/applications/new")}>New application</Button>}
        </Group>} />
      <Card withBorder>
        {loading ? <Text c="dimmed">Loading applications…</Text> : rows.length === 0 ?
          <Text c="dimmed">No applications are available in your PMS scope.</Text> :
          <Table.ScrollContainer minWidth={680}>
            <Table striped highlightOnHover>
              <Table.Thead><Table.Tr>
                <Table.Th>Application</Table.Th><Table.Th>Title</Table.Th>
                <Table.Th>Domain</Table.Th><Table.Th>Status</Table.Th><Table.Th>Created</Table.Th>
              </Table.Tr></Table.Thead>
              <Table.Tbody>{rows.map((row) => (
                <Table.Tr key={row.id} onClick={() => navigate(`/pms/applications/${row.id}`)} style={{ cursor: "pointer" }}>
                  <Table.Td>{row.application_number || "Draft"}</Table.Td>
                  <Table.Td>{row.title}</Table.Td><Table.Td>{row.technical_domain || "—"}</Table.Td>
                  <Table.Td><StatusBadge status={row.status} /></Table.Td>
                  <Table.Td>{new Date(row.created_at).toLocaleDateString()}</Table.Td>
                </Table.Tr>
              ))}</Table.Tbody>
            </Table>
          </Table.ScrollContainer>}
      </Card>
    </Container>
  );
}
