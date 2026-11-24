import { useState } from "react";
import { Alert, Badge, Button, Card, Container, Group, Modal, NumberInput, Select, Stack, Table, Text, Textarea, Title } from "@mantine/core";

import { useAuth } from "../../../auth/AuthProvider";
import { useCreateStockRequest, useDecideStockRequest, useInventoryItems, useIssueStockRequest, useStockRequests } from "../api/hooks";

export default function StockRequestsPage() {
  const { can } = useAuth();
  const { data: requests, isLoading } = useStockRequests();
  const { data: inventory } = useInventoryItems();
  const createRequest = useCreateStockRequest();

  const [createOpened, setCreateOpened] = useState(false);
  const [selectedItem, setSelectedItem] = useState<string | null>(null);
  const [quantity, setQuantity] = useState<number | string>(1);
  const [purpose, setPurpose] = useState("");

  const canRequest = can("dept.stock_request.create");
  const canApprove = can("dept.stock_request.approve");
  const canIssue = can("dept.stock_request.issue");

  const [activeReqId, setActiveReqId] = useState<string | null>(null);
  const decideMutation = useDecideStockRequest(activeReqId ?? "");
  const issueMutation = useIssueStockRequest(activeReqId ?? "");

  const handleCreate = async () => {
    if (!selectedItem || Number(quantity) <= 0 || !purpose.trim()) return;
    await createRequest.mutateAsync({
      inventory_item_id: selectedItem,
      requested_quantity: Number(quantity),
      purpose,
    });
    setSelectedItem(null);
    setQuantity(1);
    setPurpose("");
    setCreateOpened(false);
  };

  const handleDecision = async (id: string, decision: "APPROVE" | "REJECT") => {
    setActiveReqId(id);
    await decideMutation.mutateAsync({ decision });
    setActiveReqId(null);
  };

  const handleIssue = async (id: string) => {
    setActiveReqId(id);
    await issueMutation.mutateAsync({});
    setActiveReqId(null);
  };

  const statusColor = (st: string) => {
    if (st === "ISSUED") return "green";
    if (st === "APPROVED") return "blue";
    if (st === "REJECTED") return "red";
    return "yellow";
  };

  return (
    <Container size="lg" py="xl">
      <Group justify="space-between" mb="lg">
        <div>
          <Title order={2}>Stock Requests</Title>
          <Text c="dimmed">Faculty stock requisitions, HOD approvals, and admin issuance</Text>
        </div>
        {canRequest && (
          <Button onClick={() => setCreateOpened(true)}>Request Stock</Button>
        )}
      </Group>

      {isLoading && <Text>Loading requests...</Text>}

      {requests && requests.length === 0 && (
        <Alert title="No Requests" color="blue">
          There are no stock requests on record.
        </Alert>
      )}

      {requests && requests.length > 0 && (
        <Card withBorder shadow="sm" radius="md">
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Item</Table.Th>
                <Table.Th>Requested By</Table.Th>
                <Table.Th>Qty</Table.Th>
                <Table.Th>Purpose</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Actions</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {requests.map((r) => (
                <Table.Tr key={r.id}>
                  <Table.Td fw={500}>{r.item_name || r.inventory_item}</Table.Td>
                  <Table.Td>{r.requested_by_id}</Table.Td>
                  <Table.Td>{r.requested_quantity}</Table.Td>
                  <Table.Td>{r.purpose}</Table.Td>
                  <Table.Td>
                    <Badge color={statusColor(r.status)}>{r.status}</Badge>
                  </Table.Td>
                  <Table.Td>
                    <Group gap="xs">
                      {canApprove && r.status === "SUBMITTED" && (
                        <>
                          <Button size="xs" color="teal" onClick={() => handleDecision(r.id, "APPROVE")}>
                            Approve
                          </Button>
                          <Button size="xs" color="red" variant="subtle" onClick={() => handleDecision(r.id, "REJECT")}>
                            Reject
                          </Button>
                        </>
                      )}
                      {canIssue && r.status === "APPROVED" && (
                        <Button size="xs" color="indigo" onClick={() => handleIssue(r.id)}>
                          Issue Stock
                        </Button>
                      )}
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Card>
      )}

      <Modal opened={createOpened} onClose={() => setCreateOpened(false)} title="Request Stock Item">
        <Stack gap="sm">
          <Select
            label="Inventory Item"
            placeholder="Select item"
            data={inventory?.map((i) => ({ value: i.id, label: `${i.name} (${i.quantity} available)` })) || []}
            value={selectedItem}
            onChange={setSelectedItem}
            required
          />
          <NumberInput label="Requested Quantity" value={quantity} onChange={setQuantity} min={1} required />
          <Textarea label="Purpose" placeholder="State reason for stock item" value={purpose} onChange={(e) => setPurpose(e.target.value)} required />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setCreateOpened(false)}>Cancel</Button>
            <Button onClick={handleCreate} loading={createRequest.isPending}>Submit Request</Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
