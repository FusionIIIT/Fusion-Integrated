import { useState, useEffect } from "react";
import {
  Button, Card, Container, Group, Modal, Stack, Text, TextInput, Textarea
} from "@mantine/core";
import { FaPlus } from "react-icons/fa";
import { PageHeader } from "../../../ui/components/PageHeader";
import { DataTable } from "../../../ui/components/DataTable";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import type { ProjectClosure } from "../api/types";

export default function ClosuresPage() {
  const [items, setItems] = useState<ProjectClosure[]>([]);
  const [loading, setLoading] = useState(true);
  const [opened, setOpened] = useState(false);
  const [projectId, setProjectId] = useState("");
  const [summary, setSummary] = useState("");
  const [settlement, setSettlement] = useState("");
  const [assets, setAssets] = useState("");

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/v1/rspc/closures", { credentials: "include" });
      if (res.ok) {
        const data = await res.json();
        setItems(data.results ?? data);
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCreate = async () => {
    try {
      const res = await fetch("/api/v1/rspc/closures", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          project_id: parseInt(projectId),
          completion_summary: summary,
          financial_settlement_details: settlement,
          assets_declared: assets,
        }),
      });
      if (res.ok) {
        setOpened(false);
        setProjectId("");
        setSummary("");
        setSettlement("");
        setAssets("");
        fetchData();
      }
    } catch {
      // ignore
    }
  };

  return (
    <Container size="xl">
      <PageHeader
        title="Project Closures & Archival"
        subtitle="Formal project closure reports, financial settlements, and asset declarations"
        action={
          <Button leftSection={<FaPlus size={12} />} onClick={() => setOpened(true)}>
            Initiate Project Closure
          </Button>
        }
      />

      <Card padding="lg" mt="md">
        <DataTable<ProjectClosure>
          rows={items}
          loading={loading}
          rowKey={(r) => r.id}
          empty={{ title: "No project closures found", description: "Initiate project closure to get started" }}
          columns={[
            {
              key: "project",
              header: "Project ID",
              render: (r) => (
                <Stack gap={2}>
                  <Text fw={500}>Project #{r.project}</Text>
                  <Text size="xs" c="dimmed">Closure #{r.id}</Text>
                </Stack>
              ),
            },
            {
              key: "completion_summary",
              header: "Completion Summary",
              render: (r) => r.completion_summary,
            },
            {
              key: "status",
              header: "Status",
              render: (r) => <StatusBadge status={r.status} />,
            },
            {
              key: "created_at",
              header: "Submitted On",
              render: (r) => new Date(r.created_at).toLocaleDateString(),
            },
          ]}
        />
      </Card>

      <Modal opened={opened} onClose={() => setOpened(false)} title="Initiate Project Closure" size="md">
        <Stack gap="sm">
          <TextInput
            label="Project ID"
            type="number"
            required
            placeholder="e.g. 1"
            value={projectId}
            onChange={(e) => setProjectId(e.target.value)}
          />
          <Textarea
            label="Completion Summary"
            required
            placeholder="Overview of completed research deliverables..."
            value={summary}
            onChange={(e) => setSummary(e.target.value)}
          />
          <Textarea
            label="Financial Settlement Details"
            placeholder="Audit certificate, unspent balance return details..."
            value={settlement}
            onChange={(e) => setSettlement(e.target.value)}
          />
          <Textarea
            label="Assets Declared"
            placeholder="List of institute assets procured under project..."
            value={assets}
            onChange={(e) => setAssets(e.target.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setOpened(false)}>Cancel</Button>
            <Button onClick={handleCreate}>Submit Closure</Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
