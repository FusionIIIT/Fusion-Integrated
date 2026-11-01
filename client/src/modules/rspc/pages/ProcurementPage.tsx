import { useState, useEffect } from "react";
import {
  Button, Card, Container, Group, Modal, Stack, Text, TextInput, Textarea
} from "@mantine/core";
import { FaPlus } from "react-icons/fa";
import { PageHeader } from "../../../ui/components/PageHeader";
import { DataTable } from "../../../ui/components/DataTable";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import type { ProcurementRequest } from "../api/types";

export default function ProcurementPage() {
  const [items, setItems] = useState<ProcurementRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [opened, setOpened] = useState(false);
  const [itemDesc, setItemDesc] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [estimatedCost, setEstimatedCost] = useState("");
  const [justification, setJustification] = useState("");

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/v1/rspc/procurement", { credentials: "include" });
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
      const res = await fetch("/api/v1/rspc/procurement", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          item_description: itemDesc,
          quantity: parseInt(quantity) || 1,
          estimated_cost: parseFloat(estimatedCost),
          justification,
        }),
      });
      if (res.ok) {
        setOpened(false);
        setItemDesc("");
        setQuantity("1");
        setEstimatedCost("");
        setJustification("");
        fetchData();
      }
    } catch {
      // ignore
    }
  };

  return (
    <Container size="xl">
      <PageHeader
        title="Procurement Requests"
        subtitle="Request equipment and consumable procurements against sanctioned project budgets"
        action={
          <Button leftSection={<FaPlus size={12} />} onClick={() => setOpened(true)}>
            New Procurement Request
          </Button>
        }
      />

      <Card padding="lg" mt="md">
        <DataTable<ProcurementRequest>
          rows={items}
          loading={loading}
          rowKey={(r) => r.id}
          empty={{ title: "No procurement requests found", description: "Submit a procurement request to get started" }}
          columns={[
            {
              key: "item_description",
              header: "Item Description",
              render: (r) => (
                <Stack gap={2}>
                  <Text fw={500}>{r.item_description}</Text>
                  <Text size="xs" c="dimmed">Qty: {r.quantity} • Req #{r.id}</Text>
                </Stack>
              ),
            },
            {
              key: "estimated_cost",
              header: "Estimated Cost",
              render: (r) => `₹${Number(r.estimated_cost).toLocaleString()}`,
            },
            {
              key: "justification",
              header: "Justification",
              render: (r) => r.justification || "—",
            },
            {
              key: "status",
              header: "Status",
              render: (r) => <StatusBadge status={r.status} />,
            },
            {
              key: "created_at",
              header: "Requested On",
              render: (r) => new Date(r.created_at).toLocaleDateString(),
            },
          ]}
        />
      </Card>

      <Modal opened={opened} onClose={() => setOpened(false)} title="New Procurement Request" size="md">
        <Stack gap="sm">
          <TextInput
            label="Item / Equipment Description"
            required
            placeholder="e.g. Oscilloscope, High-Performance GPU"
            value={itemDesc}
            onChange={(e) => setItemDesc(e.target.value)}
          />
          <TextInput
            label="Quantity"
            type="number"
            required
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
          />
          <TextInput
            label="Estimated Total Cost (INR)"
            type="number"
            required
            placeholder="e.g. 250000"
            value={estimatedCost}
            onChange={(e) => setEstimatedCost(e.target.value)}
          />
          <Textarea
            label="Technical Justification"
            placeholder="Justification for project requirements..."
            value={justification}
            onChange={(e) => setJustification(e.target.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setOpened(false)}>Cancel</Button>
            <Button onClick={handleCreate}>Submit Request</Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
