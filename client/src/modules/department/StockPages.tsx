import { Button, Container, Group, NumberInput, Paper, Stack, Text, TextInput } from "@mantine/core";
import { useState } from "react";

import { useAuth } from "../../auth/AuthProvider";
import { ErrorState } from "../../ui/components/ErrorState";
import { PageHeader } from "../../ui/components/PageHeader";
import { useDepartmentAction, useDepartmentFeed } from "./api";
import { FeedState } from "./FeedState";

interface Item { id: number; name: string; quantity: number }
interface StockRequest { id: number; item_name: string; quantity: number; status: string }

export function InventoryPage() {
  const { can } = useAuth();
  const feed = useDepartmentFeed<Item>("inventory");
  const action = useDepartmentAction();
  const [name, setName] = useState("");
  const [quantity, setQuantity] = useState<number | string>(1);
  const [requested, setRequested] = useState<number | null>(null);
  const [requestQuantity, setRequestQuantity] = useState<number | string>(1);

  return (
    <Container size="md" py="lg">
      <PageHeader title="Department inventory" />
      <Stack>
        {can("department.stock.create") && (
          <Paper withBorder p="md" component="form" onSubmit={(event) => {
            event.preventDefault();
            if (!name.trim() || typeof quantity !== "number") return;
            action.mutate({ path: "inventory", data: { name, quantity } }, {
              onSuccess: () => { setName(""); setQuantity(1); },
            });
          }}>
            <Stack>
              <TextInput label="Item name" value={name} required maxLength={160}
                onChange={(event) => setName(event.currentTarget.value)} />
              <NumberInput label="Quantity to add" min={1} max={1000000} allowDecimal={false}
                value={quantity} onChange={setQuantity} required />
              <Button type="submit" loading={action.isPending}>Add stock</Button>
            </Stack>
          </Paper>
        )}
        {feed.rows.map((item) => (
          <Paper key={item.id} withBorder p="md">
            <Group justify="space-between">
              <div><Text fw={600}>{item.name}</Text><Text c="dimmed">{item.quantity} available</Text></div>
              {can("department.stock_request.create") && item.quantity > 0 && (
                <Button variant="default" onClick={() => { setRequested(item.id); setRequestQuantity(1); }}>
                  Request {item.name}
                </Button>
              )}
            </Group>
            {requested === item.id && (
              <form onSubmit={(event) => {
                event.preventDefault();
                if (typeof requestQuantity !== "number") return;
                action.mutate({ path: "stock-requests", data: { item_id: item.id, quantity: requestQuantity } }, {
                  onSuccess: () => setRequested(null),
                });
              }}>
                <Group mt="md" align="end">
                  <NumberInput label="Quantity to request" min={1} max={item.quantity}
                    allowDecimal={false} value={requestQuantity} onChange={setRequestQuantity} required />
                  <Button type="submit" loading={action.isPending}>Submit request</Button>
                  <Button variant="subtle" onClick={() => setRequested(null)}>Cancel</Button>
                </Group>
              </form>
            )}
          </Paper>
        ))}
        {action.isError && <ErrorState error={action.error} />}
        {action.isSuccess && <Text role="status">Saved.</Text>}
        <FeedState query={feed} empty="No inventory items are available." />
      </Stack>
    </Container>
  );
}

export function StockRequestsPage() {
  const { can } = useAuth();
  const feed = useDepartmentFeed<StockRequest>("stock-requests");
  const action = useDepartmentAction();
  const canReview = can("department.stock_request.approve");
  const canIssue = can("department.stock_request.update");
  const run = (id: number, decision: string) => action.mutate({
    path: `stock-requests/${id}/action`, data: { action: decision },
  });

  return (
    <Container size="md" py="lg">
      <PageHeader title={canReview || canIssue ? "Stock requests" : "Issued stock history"} />
      <Stack>
        {feed.rows.map((request) => (
          <Paper key={request.id} withBorder p="md">
            <Group justify="space-between">
              <Text>{request.item_name} · {request.quantity} · {request.status}</Text>
              {canReview && request.status === "pending" && (
                <Group>
                  <Button disabled={action.isPending} onClick={() => run(request.id, "approve")}>Approve</Button>
                  <Button variant="default" disabled={action.isPending}
                    onClick={() => run(request.id, "reject")}>Reject</Button>
                </Group>
              )}
              {canIssue && request.status === "approved" && (
                <Button disabled={action.isPending} onClick={() => run(request.id, "issue")}>Issue stock</Button>
              )}
            </Group>
          </Paper>
        ))}
        {action.isError && <ErrorState error={action.error} />}
        <FeedState query={feed} empty="No stock requests to show." />
      </Stack>
    </Container>
  );
}
