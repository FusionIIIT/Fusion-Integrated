import { Button, Group, Loader, Stack, Table, TextInput, Title } from "@mantine/core";
import { useEffect, useState } from "react";
import { Navigate, type RouteObject, useParams } from "react-router-dom";

type PatentApplication = {
  id: number;
  applicationCode?: string;
  title?: string;
  status?: string;
};

function PmsListPage() {
  const [rows, setRows] = useState<PatentApplication[]>([]);
  const [loading, setLoading] = useState(false);
  const [query, setQuery] = useState("");

  async function loadData(search = "") {
    setLoading(true);
    try {
      const url = search ? `/api/pms/applications?search=${encodeURIComponent(search)}` : "/api/pms/applications";
      const response = await fetch(url);
      const result = await response.json();
      setRows(result.data || []);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  return (
    <Stack>
      <Title order={2}>Patent Applications</Title>
      <Group>
        <TextInput
          placeholder="Search by title/code"
          value={query}
          onChange={(e) => setQuery(e.currentTarget.value)}
        />
        <Button onClick={() => loadData(query)}>Search</Button>
      </Group>
      {loading ? <Loader /> : (
        <Table striped>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>ID</Table.Th>
              <Table.Th>Code</Table.Th>
              <Table.Th>Title</Table.Th>
              <Table.Th>Status</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {rows.map((row) => (
              <Table.Tr key={row.id}>
                <Table.Td>{row.id}</Table.Td>
                <Table.Td>{row.applicationCode || "-"}</Table.Td>
                <Table.Td>{row.title || "-"}</Table.Td>
                <Table.Td>{row.status || "-"}</Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}
    </Stack>
  );
}

function PmsDetailPage() {
  const params = useParams();
  const [row, setRow] = useState<PatentApplication | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function loadData() {
      if (!params.id) {
        return;
      }
      setLoading(true);
      try {
        const response = await fetch(`/api/pms/applications/${params.id}`);
        const result = await response.json();
        setRow(result.data || null);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [params.id]);

  if (loading) {
    return <Loader />;
  }

  if (!row) {
    return <div>Patent application not found.</div>;
  }

  return (
    <Stack>
      <Title order={2}>Patent Detail</Title>
      <div><strong>ID:</strong> {row.id}</div>
      <div><strong>Code:</strong> {row.applicationCode || "-"}</div>
      <div><strong>Title:</strong> {row.title || "-"}</div>
      <div><strong>Status:</strong> {row.status || "-"}</div>
    </Stack>
  );
}

function PmsFormPage() {
  const [loading, setLoading] = useState(false);

  async function createDraft() {
    setLoading(true);
    try {
      await fetch("/api/pms/applications/draft", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          applicantId: 1,
          title: "Draft patent title",
          abstract: "Draft abstract",
          detailedDescription: "Draft description",
          claims: "Draft claims",
          supportingDocumentMimeType: "application/pdf",
          supportingDocumentSizeMb: 1,
        }),
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <Stack>
      <Title order={2}>New Patent Application</Title>
      <Button onClick={createDraft} loading={loading}>Create Sample Draft</Button>
    </Stack>
  );
}

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="applications" replace /> },
  { path: "applications", element: <PmsListPage /> },
  { path: "applications/new", element: <PmsFormPage /> },
  { path: "applications/:id", element: <PmsDetailPage /> },
];
