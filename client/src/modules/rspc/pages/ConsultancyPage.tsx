import { useState, useEffect } from "react";
import {
  Button, Card, Container, Group, Modal, Stack, Text, TextInput, Textarea
} from "@mantine/core";
import { FaPlus } from "react-icons/fa";
import { PageHeader } from "../../../ui/components/PageHeader";
import { DataTable } from "../../../ui/components/DataTable";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import type { ConsultancyProject } from "../api/types";

export default function ConsultancyPage() {
  const [items, setItems] = useState<ConsultancyProject[]>([]);
  const [loading, setLoading] = useState(true);
  const [opened, setOpened] = useState(false);
  const [title, setTitle] = useState("");
  const [clientName, setClientName] = useState("");
  const [totalAmount, setTotalAmount] = useState("");
  const [scope, setScope] = useState("");

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/v1/rspc/consultancy", { credentials: "include" });
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
      const res = await fetch("/api/v1/rspc/consultancy", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          title,
          client_name: clientName,
          total_amount: totalAmount ? parseFloat(totalAmount) : null,
          scope,
        }),
      });
      if (res.ok) {
        setOpened(false);
        setTitle("");
        setClientName("");
        setTotalAmount("");
        setScope("");
        fetchData();
      }
    } catch {
      // ignore
    }
  };

  return (
    <Container size="xl">
      <PageHeader
        title="Consultancy Projects"
        subtitle="Manage industrial consultancy and client-funded projects"
        action={
          <Button leftSection={<FaPlus size={12} />} onClick={() => setOpened(true)}>
            Register Consultancy
          </Button>
        }
      />

      <Card padding="lg" mt="md">
        <DataTable<ConsultancyProject>
          rows={items}
          loading={loading}
          rowKey={(r) => r.id}
          empty={{ title: "No consultancy projects found", description: "Register a consultancy project to get started" }}
          columns={[
            {
              key: "title",
              header: "Project Title",
              render: (r) => (
                <Stack gap={2}>
                  <Text fw={500}>{r.title}</Text>
                  <Text size="xs" c="dimmed">Client: {r.client_name || "—"}</Text>
                </Stack>
              ),
            },
            {
              key: "total_amount",
              header: "Total Amount",
              render: (r) => r.total_amount ? `₹${Number(r.total_amount).toLocaleString()}` : "—",
            },
            {
              key: "status",
              header: "Status",
              render: (r) => <StatusBadge status={r.status} />,
            },
            {
              key: "created_at",
              header: "Registered On",
              render: (r) => new Date(r.created_at).toLocaleDateString(),
            },
          ]}
        />
      </Card>

      <Modal opened={opened} onClose={() => setOpened(false)} title="Register Consultancy Project" size="lg">
        <Stack gap="sm">
          <TextInput
            label="Project Title"
            required
            placeholder="Consultancy title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
          <TextInput
            label="Client Name / Organization"
            required
            placeholder="e.g. BHEL, TCS, L&T"
            value={clientName}
            onChange={(e) => setClientName(e.target.value)}
          />
          <TextInput
            label="Total Agreed Amount (INR)"
            type="number"
            placeholder="e.g. 1500000"
            value={totalAmount}
            onChange={(e) => setTotalAmount(e.target.value)}
          />
          <Textarea
            label="Scope and Deliverables"
            placeholder="Describe deliverables and milestones..."
            minRows={3}
            value={scope}
            onChange={(e) => setScope(e.target.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setOpened(false)}>Cancel</Button>
            <Button onClick={handleCreate}>Save Project</Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
