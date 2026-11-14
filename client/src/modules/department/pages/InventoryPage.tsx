import { useState } from "react";
import {
  Button,
  Card,
  Container,
  Group,
  Stack,
  Table,
  Tabs,
  Text,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  FaCheck,
  FaClipboardList,
  FaExchangeAlt,
  FaPlus,
  FaTimes,
  FaWarehouse,
} from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useDecideStockRequest,
  useDepartments,
  useInventory,
  useIssueStockRequest,
  useStockRequests,
} from "../api/hooks";
import { DepartmentStatusBadge } from "../components/DepartmentStatusBadge";
import { InsertStockModal } from "../components/InsertStockModal";
import { RequestStockModal } from "../components/RequestStockModal";

export default function InventoryPage() {
  const { can } = useAuth();
  const { data: depts } = useDepartments();
  const defaultDept = depts?.[0];
  const deptId = defaultDept?.id;

  const { data: inventory, isPending: invLoading, error: invError } = useInventory(deptId);
  const { data: requests, isPending: reqLoading, error: reqError } = useStockRequests(deptId);

  const decideReq = useDecideStockRequest();
  const issueReq = useIssueStockRequest();

  const [activeTab, setActiveTab] = useState<string | null>("inventory");
  const [requestModal, setRequestModal] = useState(false);
  const [insertModal, setInsertModal] = useState(false);

  const canManage = can("department.inventory.manage");
  const canRequest = can("department.stock_request.create");

  if (invError || reqError) {
    return <Container size="lg"><ErrorState error={invError || reqError} /></Container>;
  }

  const handleDecide = async (id: number, status: "approved" | "rejected") => {
    try {
      await decideReq.mutateAsync({ id, status });
      notifications.show({
        title: `Request ${status}`,
        message: `Stock request #${id} has been marked ${status}.`,
        color: status === "approved" ? "teal" : "red",
      });
    } catch {
      notifications.show({
        title: "Action failed",
        message: "Could not decide stock request.",
        color: "red",
      });
    }
  };

  const handleIssue = async (id: number) => {
    try {
      await issueReq.mutateAsync(id);
      notifications.show({
        title: "Stock Issued",
        message: `Items for request #${id} have been issued from inventory.`,
        color: "teal",
      });
    } catch {
      notifications.show({
        title: "Issuance failed",
        message: "Could not issue requested stock (check inventory balance).",
        color: "red",
      });
    }
  };

  return (
    <Container size="lg">
      <PageHeader
        title="Department Inventory & Stock"
        subtitle="Hardware, consumables, lab components and requisition workflows"
        action={
          <Group gap="xs">
            {canRequest && deptId && (
              <Button
                leftSection={<FaExchangeAlt size={12} />}
                onClick={() => setRequestModal(true)}
              >
                Request Stock
              </Button>
            )}
            {canManage && deptId && (
              <Button
                variant="light"
                leftSection={<FaPlus size={12} />}
                onClick={() => setInsertModal(true)}
              >
                Add Inventory
              </Button>
            )}
          </Group>
        }
      />

      <Tabs value={activeTab} onChange={setActiveTab} mb="lg">
        <Tabs.List>
          <Tabs.Tab
            value="inventory"
            leftSection={<FaWarehouse size={14} />}
          >
            Inventory Items ({(inventory || []).length})
          </Tabs.Tab>
          <Tabs.Tab
            value="requests"
            leftSection={<FaClipboardList size={14} />}
          >
            Stock Requests ({(requests || []).length})
          </Tabs.Tab>
        </Tabs.List>

        {/* Tab 1: Inventory Items */}
        <Tabs.Panel value="inventory" pt="md">
          {invLoading && <Text c="dimmed">Loading inventory…</Text>}

          {!invLoading && (inventory || []).length === 0 && (
            <Card padding="xl" withBorder>
              <Stack align="center" gap={6}>
                <FaWarehouse size={28} color="var(--mantine-color-gray-5)" />
                <Text fw={600}>No inventory items recorded yet</Text>
              </Stack>
            </Card>
          )}

          {(inventory || []).length > 0 && (
            <Card padding="0" withBorder>
              <Table striped highlightOnHover>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Item Name</Table.Th>
                    <Table.Th>Available Stock</Table.Th>
                    <Table.Th>Unit</Table.Th>
                    <Table.Th>Last Updated</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {(inventory || []).map((item) => (
                    <Table.Tr key={item.id}>
                      <Table.Td fw={600}>{item.name}</Table.Td>
                      <Table.Td>
                        <Text
                          fw={700}
                          c={item.quantity === 0 ? "red" : item.quantity < 5 ? "orange" : undefined}
                        >
                          {item.quantity}
                        </Text>
                      </Table.Td>
                      <Table.Td>{item.unit || "units"}</Table.Td>
                      <Table.Td>
                        <Text size="xs" c="dimmed">
                          {new Date(item.updated_at).toLocaleDateString()}
                        </Text>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Card>
          )}
        </Tabs.Panel>

        {/* Tab 2: Stock Requests */}
        <Tabs.Panel value="requests" pt="md">
          {reqLoading && <Text c="dimmed">Loading requests…</Text>}

          {!reqLoading && (requests || []).length === 0 && (
            <Card padding="xl" withBorder>
              <Stack align="center" gap={6}>
                <FaClipboardList size={28} color="var(--mantine-color-gray-5)" />
                <Text fw={600}>No stock requisitions found</Text>
              </Stack>
            </Card>
          )}

          {(requests || []).length > 0 && (
            <Card padding="0" withBorder>
              <Table striped highlightOnHover>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Req ID</Table.Th>
                    <Table.Th>Item</Table.Th>
                    <Table.Th>Quantity</Table.Th>
                    <Table.Th>Requester</Table.Th>
                    <Table.Th>Status</Table.Th>
                    <Table.Th>Date</Table.Th>
                    <Table.Th>Actions</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {(requests || []).map((req) => {
                    const item = (inventory || []).find((i) => i.id === req.item);
                    return (
                      <Table.Tr key={req.id}>
                        <Table.Td>#{req.id}</Table.Td>
                        <Table.Td fw={600}>{item ? item.name : `Item #${req.item}`}</Table.Td>
                        <Table.Td>{req.quantity}</Table.Td>
                        <Table.Td>User #{req.requester_user_id}</Table.Td>
                        <Table.Td>
                          <DepartmentStatusBadge status={req.status} />
                        </Table.Td>
                        <Table.Td>
                          <Text size="xs" c="dimmed">
                            {new Date(req.created_at).toLocaleDateString()}
                          </Text>
                        </Table.Td>
                        <Table.Td>
                          <Group gap="xs">
                            {req.status === "pending" && canManage && (
                              <>
                                <Button
                                  size="compact-xs"
                                  color="teal"
                                  leftSection={<FaCheck size={10} />}
                                  loading={decideReq.isPending}
                                  onClick={() => handleDecide(req.id, "approved")}
                                >
                                  Approve
                                </Button>
                                <Button
                                  size="compact-xs"
                                  color="red"
                                  variant="light"
                                  leftSection={<FaTimes size={10} />}
                                  loading={decideReq.isPending}
                                  onClick={() => handleDecide(req.id, "rejected")}
                                >
                                  Reject
                                </Button>
                              </>
                            )}

                            {req.status === "approved" && canManage && (
                              <Button
                                size="compact-xs"
                                color="indigo"
                                leftSection={<FaCheck size={10} />}
                                loading={issueReq.isPending}
                                onClick={() => handleIssue(req.id)}
                              >
                                Issue Stock
                              </Button>
                            )}
                          </Group>
                        </Table.Td>
                      </Table.Tr>
                    );
                  })}
                </Table.Tbody>
              </Table>
            </Card>
          )}
        </Tabs.Panel>
      </Tabs>

      {deptId && (
        <>
          <RequestStockModal
            opened={requestModal}
            onClose={() => setRequestModal(false)}
            departmentId={deptId}
          />
          <InsertStockModal
            opened={insertModal}
            onClose={() => setInsertModal(false)}
            departmentId={deptId}
          />
        </>
      )}
    </Container>
  );
}
