import {
  Alert,
  Badge,
  Button,
  Card,
  Container,
  Group,
  Loader,
  Modal,
  Paper,
  SimpleGrid,
  Stack,
  Table,
  Tabs,
  Text,
  Textarea,
  Title,
} from "@mantine/core";
import { useState } from "react";
import {
  FaBoxOpen,
  FaCheck,
  FaCheckCircle,
  FaCheckDouble,
  FaInfoCircle,
  FaTimes,
  FaUserCheck,
} from "react-icons/fa";

import {
  useApproveBooking,
  useApproveReplenishment,
  useBookings,
  useRejectBooking,
  useRejectReplenishment,
  useReplenishments,
} from "../api/hooks";
import type { Booking, InventoryReplenishment } from "../api/types";

export default function HostelApprovalsPage() {
  const { data: bookings, isLoading: loadingBookings, refetch: refetchBookings } = useBookings();
  const { data: replenishments, isLoading: loadingReplenishments, refetch: refetchReplenishments } = useReplenishments();

  const approveBooking = useApproveBooking();
  const rejectBooking = useRejectBooking();
  const approveReplenishment = useApproveReplenishment();
  const rejectReplenishment = useRejectReplenishment();

  const [activeTab, setActiveTab] = useState<string | null>("bookings");

  // Booking approval/rejection modal states
  const [selectedBooking, setSelectedBooking] = useState<Booking | null>(null);
  const [approveModalOpen, setApproveModalOpen] = useState(false);
  const [approveRemarks, setApproveRemarks] = useState("");
  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [rejectRemarks, setRejectRemarks] = useState("");

  // Replenishment modal state
  const [selectedReplenishment, setSelectedReplenishment] = useState<InventoryReplenishment | null>(null);
  const [repRejectModalOpen, setRepRejectModalOpen] = useState(false);

  // Filter forwarded bookings
  const forwardedBookings = (bookings || []).filter((b) => b.status === "FORWARDED");
  const pendingReplenishments = (replenishments || []).filter((r) => r.status === "PENDING");

  // Booking handlers
  const handleOpenApprove = (booking: Booking) => {
    setSelectedBooking(booking);
    setApproveRemarks("");
    setApproveModalOpen(true);
  };

  const handleConfirmApprove = async () => {
    if (!selectedBooking) return;
    await approveBooking.mutateAsync({
      id: selectedBooking.id,
      remarks: approveRemarks,
    });
    setApproveModalOpen(false);
    setSelectedBooking(null);
  };

  const handleOpenReject = (booking: Booking) => {
    setSelectedBooking(booking);
    setRejectRemarks("");
    setRejectModalOpen(true);
  };

  const handleConfirmReject = async () => {
    if (!selectedBooking) return;
    await rejectBooking.mutateAsync({
      id: selectedBooking.id,
      remarks: rejectRemarks,
    });
    setRejectModalOpen(false);
    setSelectedBooking(null);
  };

  // Replenishment handlers
  const handleApproveReplenishment = async (id: number) => {
    await approveReplenishment.mutateAsync(id);
  };

  const handleOpenRejectReplenishment = (item: InventoryReplenishment) => {
    setSelectedReplenishment(item);
    setRepRejectModalOpen(true);
  };

  const handleConfirmRejectReplenishment = async () => {
    if (!selectedReplenishment) return;
    await rejectReplenishment.mutateAsync(selectedReplenishment.id);
    setRepRejectModalOpen(false);
    setSelectedReplenishment(null);
  };

  return (
    <Container size="xl" py="xl">
      <Stack gap="lg">
        {/* Header */}
        <Group justify="space-between" align="flex-start">
          <div>
            <Title order={2}>Visitors Hostel In-Charge Approvals</Title>
            <Text c="dimmed" size="sm">
              Review and sanction bookings and inventory requests routed by the Caretaker (UC-VH-003, BR-VH-003)
            </Text>
          </div>
          <Group>
            <Button
              variant="default"
              onClick={() => {
                refetchBookings();
                refetchReplenishments();
              }}
              leftSection={<FaCheckDouble />}
            >
              Refresh
            </Button>
          </Group>
        </Group>

        {/* Stats Row */}
        <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
          <Paper withBorder p="md" radius="md">
            <Group justify="space-between">
              <div>
                <Text size="xs" c="dimmed" fw={700} tt="uppercase">
                  Pending Booking Approvals
                </Text>
                <Title order={3}>{forwardedBookings.length}</Title>
              </div>
              <FaUserCheck size={28} color="#228be6" />
            </Group>
          </Paper>

          <Paper withBorder p="md" radius="md">
            <Group justify="space-between">
              <div>
                <Text size="xs" c="dimmed" fw={700} tt="uppercase">
                  Pending Inventory Replenishments
                </Text>
                <Title order={3}>{pendingReplenishments.length}</Title>
              </div>
              <FaBoxOpen size={28} color="#fd7e14" />
            </Group>
          </Paper>
        </SimpleGrid>

        {/* Tabs for Booking Approvals & Inventory Replenishments */}
        <Card withBorder radius="md" p="md">
          <Tabs value={activeTab} onChange={setActiveTab}>
            <Tabs.List mb="md">
              <Tabs.Tab
                value="bookings"
                leftSection={<FaCheckDouble size={14} />}
                rightSection={<Badge size="xs" circle color="blue">{forwardedBookings.length}</Badge>}
              >
                Forwarded Bookings
              </Tabs.Tab>
              <Tabs.Tab
                value="replenishments"
                leftSection={<FaBoxOpen size={14} />}
                rightSection={<Badge size="xs" circle color="orange">{pendingReplenishments.length}</Badge>}
              >
                Inventory Replenishments
              </Tabs.Tab>
            </Tabs.List>

            {/* Bookings Approvals Panel */}
            <Tabs.Panel value="bookings">
              {loadingBookings ? (
                <Group justify="center" p="xl">
                  <Loader size="md" />
                </Group>
              ) : forwardedBookings.length === 0 ? (
                <Alert icon={<FaCheckCircle size={16} />} title="All Clear" color="teal">
                  There are no pending booking requisitions awaiting your administrative approval.
                </Alert>
              ) : (
                <Table striped highlightOnHover withTableBorder withColumnBorders>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Reference</Table.Th>
                      <Table.Th>Visitor & Purpose</Table.Th>
                      <Table.Th>Category</Table.Th>
                      <Table.Th>Dates of Stay</Table.Th>
                      <Table.Th>Requirements</Table.Th>
                      <Table.Th>Billing</Table.Th>
                      <Table.Th>Caretaker Remarks</Table.Th>
                      <Table.Th>Action</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {forwardedBookings.map((b) => (
                      <Table.Tr key={b.id}>
                        <Table.Td>
                          <Text fw={600} size="sm">{b.booking_reference}</Text>
                          <Text size="xs" c="dimmed">Indenter #{b.indenter_id}</Text>
                        </Table.Td>
                        <Table.Td>
                          <Text fw={600} size="sm">{b.visitor_name}</Text>
                          <Text size="xs" c="dimmed" lineClamp={2}>
                            {b.visit_purpose || "No purpose provided"}
                          </Text>
                          <Text size="xs" c="dimmed">{b.visitor_phone}</Text>
                        </Table.Td>
                        <Table.Td>
                          <Badge color="blue" variant="outline">
                            Cat {b.category_code || b.visitor_category}
                          </Badge>
                        </Table.Td>
                        <Table.Td>
                          <Text size="xs" fw={500}>{b.check_in_date}</Text>
                          <Text size="xs" c="dimmed">to</Text>
                          <Text size="xs" fw={500}>{b.check_out_date}</Text>
                        </Table.Td>
                        <Table.Td>
                          <Text size="sm">{b.number_of_rooms} Room(s)</Text>
                          <Text size="xs" c="dimmed">{b.number_of_occupants} Guest(s)</Text>
                        </Table.Td>
                        <Table.Td>
                          <Badge size="xs" variant="dot">
                            {b.billing_responsibility}
                          </Badge>
                        </Table.Td>
                        <Table.Td>
                          <Text size="xs" fs="italic">
                            {b.caretaker_remarks || "No remarks"}
                          </Text>
                        </Table.Td>
                        <Table.Td>
                          <Group gap="xs">
                            <Button
                              size="xs"
                              color="teal"
                              leftSection={<FaCheck size={12} />}
                              onClick={() => handleOpenApprove(b)}
                            >
                              Approve
                            </Button>
                            <Button
                              size="xs"
                              color="red"
                              variant="subtle"
                              leftSection={<FaTimes size={12} />}
                              onClick={() => handleOpenReject(b)}
                            >
                              Reject
                            </Button>
                          </Group>
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              )}
            </Tabs.Panel>

            {/* Inventory Replenishments Panel */}
            <Tabs.Panel value="replenishments">
              {loadingReplenishments ? (
                <Group justify="center" p="xl">
                  <Loader size="md" />
                </Group>
              ) : (replenishments || []).length === 0 ? (
                <Alert icon={<FaInfoCircle size={16} />} title="No Replenishment Requests" color="blue">
                  No inventory replenishment requests have been logged.
                </Alert>
              ) : (
                <Table striped highlightOnHover withTableBorder withColumnBorders>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>ID</Table.Th>
                      <Table.Th>Item</Table.Th>
                      <Table.Th>Quantity Requested</Table.Th>
                      <Table.Th>Requested By</Table.Th>
                      <Table.Th>Date</Table.Th>
                      <Table.Th>Status</Table.Th>
                      <Table.Th>Remarks</Table.Th>
                      <Table.Th>Decision</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {(replenishments || []).map((r) => (
                      <Table.Tr key={r.id}>
                        <Table.Td>#{r.id}</Table.Td>
                        <Table.Td>
                          <Text fw={600} size="sm">{r.item_name || `Item #${r.item}`}</Text>
                        </Table.Td>
                        <Table.Td>
                          <Badge size="lg" variant="light" color="blue">
                            {r.quantity_requested}
                          </Badge>
                        </Table.Td>
                        <Table.Td>User #{r.requested_by_user_id}</Table.Td>
                        <Table.Td>
                          <Text size="xs">{new Date(r.created_at).toLocaleDateString()}</Text>
                        </Table.Td>
                        <Table.Td>
                          <Badge
                            color={
                              r.status === "APPROVED"
                                ? "teal"
                                : r.status === "REJECTED"
                                ? "red"
                                : "yellow"
                            }
                          >
                            {r.status}
                          </Badge>
                        </Table.Td>
                        <Table.Td>
                          <Text size="xs">{r.remarks || "—"}</Text>
                        </Table.Td>
                        <Table.Td>
                          {r.status === "PENDING" ? (
                            <Group gap="xs">
                              <Button
                                size="xs"
                                color="teal"
                                loading={approveReplenishment.isPending}
                                onClick={() => handleApproveReplenishment(r.id)}
                              >
                                Approve
                              </Button>
                              <Button
                                size="xs"
                                color="red"
                                variant="subtle"
                                onClick={() => handleOpenRejectReplenishment(r)}
                              >
                                Reject
                              </Button>
                            </Group>
                          ) : (
                            <Text size="xs" c="dimmed">Completed</Text>
                          )}
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              )}
            </Tabs.Panel>
          </Tabs>
        </Card>
      </Stack>

      {/* Approve Booking Modal */}
      <Modal
        opened={approveModalOpen}
        onClose={() => setApproveModalOpen(false)}
        title={<Text fw={600}>Approve Requisition #{selectedBooking?.booking_reference}</Text>}
      >
        <Stack gap="md">
          <Text size="sm">
            Approve requisition for visitor <b>{selectedBooking?.visitor_name}</b> ({selectedBooking?.number_of_rooms} room(s) from {selectedBooking?.check_in_date} to {selectedBooking?.check_out_date}).
          </Text>
          <Textarea
            label="In-Charge Remarks / Sanction Notes (Optional)"
            placeholder="E.g., Approved as per institute guest protocol..."
            value={approveRemarks}
            onChange={(e) => setApproveRemarks(e.target.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setApproveModalOpen(false)}>
              Cancel
            </Button>
            <Button
              color="teal"
              loading={approveBooking.isPending}
              onClick={handleConfirmApprove}
            >
              Confirm Approval
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Reject Booking Modal */}
      <Modal
        opened={rejectModalOpen}
        onClose={() => setRejectModalOpen(false)}
        title={<Text fw={600} c="red">Reject Requisition #{selectedBooking?.booking_reference}</Text>}
      >
        <Stack gap="md">
          <Text size="sm">
            Reject requisition for <b>{selectedBooking?.visitor_name}</b>. Please specify a clear administrative reason.
          </Text>
          <Textarea
            required
            label="Rejection Reason"
            placeholder="Reason for declining the hostel booking..."
            value={rejectRemarks}
            onChange={(e) => setRejectRemarks(e.target.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setRejectModalOpen(false)}>
              Back
            </Button>
            <Button
              color="red"
              loading={rejectBooking.isPending}
              disabled={!rejectRemarks.trim()}
              onClick={handleConfirmReject}
            >
              Confirm Rejection
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Reject Replenishment Modal */}
      <Modal
        opened={repRejectModalOpen}
        onClose={() => setRepRejectModalOpen(false)}
        title={<Text fw={600} c="red">Reject Inventory Replenishment</Text>}
      >
        <Stack gap="md">
          <Text size="sm">
            Reject replenishment request for item <b>{selectedReplenishment?.item_name}</b> (Qty: {selectedReplenishment?.quantity_requested}).
          </Text>
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setRepRejectModalOpen(false)}>
              Cancel
            </Button>
            <Button
              color="red"
              loading={rejectReplenishment.isPending}
              onClick={handleConfirmRejectReplenishment}
            >
              Confirm Reject
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
