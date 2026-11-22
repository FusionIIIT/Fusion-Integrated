import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Divider,
  Group,
  Modal,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaMoneyBillWave } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useBookingBill, useBookings, useSettleBill } from "../api/hooks";
import type { BillLineItem } from "../api/types";

export default function BillingSettlementPage() {
  const { data: bookings, error } = useBookings();
  const [selectedBookingId, setSelectedBookingId] = useState<string>("");
  const [settling, setSettling] = useState(false);
  const [receiptNumber, setReceiptNumber] = useState("");
  const [settleAmount, setSettleAmount] = useState("");
  const [settleNotes, setSettleNotes] = useState("");

  const bId = Number(selectedBookingId) || 0;
  const { data: bill } = useBookingBill(bId);
  const settleMutation = useSettleBill(bill?.id ?? 0);

  const handleSettleSubmit = async () => {
    if (!bill || !receiptNumber.trim() || !settleAmount.trim()) {
      notifications.show({
        color: "red",
        message: "Receipt number and settlement amount are required.",
      });
      return;
    }

    try {
      await settleMutation.mutateAsync({
        amount_paid: settleAmount.trim(),
        receipt_number: receiptNumber.trim(),
        notes: settleNotes.trim(),
      });
      notifications.show({
        color: "teal",
        message: "Offline cash settlement recorded successfully. Bill is now settled.",
      });
      setSettling(false);
    } catch (err) {
      notifications.show({ color: "red", message: errorMessage(err) });
    }
  };

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  const eligibleBookings = (bookings ?? []).filter((b) =>
    ["checked_in", "checked_out", "cancelled", "cancellation_requested"].includes(b.status)
  );

  return (
    <Container size="lg">
      <PageHeader
        title="Billing & Offline Settlement"
        subtitle="Itemized invoice calculation, guest bill verification, and official offline cash settlement."
      />

      <Stack gap="lg">
        <Card padding="lg" withBorder>
          <Select
            label="Select Booking for Billing Review"
            placeholder="Choose stay or cancelled booking"
            data={eligibleBookings.map((b) => ({
              value: String(b.id),
              label: `${b.booking_reference} - ${b.visitors[0]?.name ?? "Guest"} (Status: ${b.status})`,
            }))}
            value={selectedBookingId}
            onChange={(val) => {
              setSelectedBookingId(val || "");
              setSettling(false);
            }}
          />
        </Card>

        {bId > 0 && bill && (
          <Card padding="xl" withBorder>
            <Group justify="space-between" mb="md">
              <div>
                <Text fw={700} size="xl">
                  Invoice {bill.bill_number}
                </Text>
                <Text size="xs" c="dimmed">
                  Responsibility: {bill.billing_responsibility.toUpperCase()} | Visitor Category: {bill.visitor_category}
                </Text>
              </div>
              <Badge size="lg" color={bill.status === "settled" ? "teal" : "blue"}>
                {bill.status.toUpperCase()}
              </Badge>
            </Group>

            <Table striped withTableBorder mt="md">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Line Item Description</Table.Th>
                  <Table.Th>Type</Table.Th>
                  <Table.Th>Quantity</Table.Th>
                  <Table.Th>Rate (₹)</Table.Th>
                  <Table.Th>Total (₹)</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {bill.items?.map((item: BillLineItem) => (
                  <Table.Tr key={item.id}>
                    <Table.Td>{item.description}</Table.Td>
                    <Table.Td>
                      <Badge size="xs" variant="outline">
                        {item.item_type}
                      </Badge>
                    </Table.Td>
                    <Table.Td>{item.quantity}</Table.Td>
                    <Table.Td>₹{item.unit_price}</Table.Td>
                    <Table.Td>
                      <Text fw={500}>₹{item.total_price}</Text>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>

            <Divider my="md" />

            <Group justify="space-between">
              <div>
                {bill.settlement && (
                  <Text size="sm" c="teal" fw={500}>
                    Settled under Receipt: {bill.settlement.receipt_number} (₹{bill.settlement.amount_paid})
                  </Text>
                )}
              </div>
              <Stack gap="xs" align="flex-end">
                <Text size="lg" fw={700}>
                  Total Amount: ₹{bill.total_amount}
                </Text>
                {bill.status !== "settled" && (
                  <Button
                    color="teal"
                    leftSection={<FaMoneyBillWave size={14} />}
                    onClick={() => {
                      setSettleAmount(bill.total_amount);
                      setReceiptNumber(`RCP-${new Date().getFullYear()}-${bill.id}`);
                      setSettling(true);
                    }}
                  >
                    Record Cash Settlement
                  </Button>
                )}
              </Stack>
            </Group>
          </Card>
        )}
      </Stack>

      {/* Settle Modal */}
      <Modal
        opened={settling}
        onClose={() => setSettling(false)}
        title="Record Offline Cash Settlement"
      >
        <Stack gap="md">
          <Text size="sm">
            Confirming offline cash collection for bill <strong>{bill?.bill_number}</strong>.
          </Text>
          <TextInput
            label="Official Receipt / Voucher Number"
            required
            value={receiptNumber}
            onChange={(e) => setReceiptNumber(e.currentTarget.value)}
          />
          <TextInput
            label="Amount Collected (INR)"
            required
            value={settleAmount}
            onChange={(e) => setSettleAmount(e.currentTarget.value)}
          />
          <Textarea
            label="Settlement Remarks"
            placeholder="Cash received at Caretaker desk..."
            value={settleNotes}
            onChange={(e) => setSettleNotes(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setSettling(false)}>
              Cancel
            </Button>
            <Button
              color="teal"
              loading={settleMutation.isPending}
              onClick={handleSettleSubmit}
            >
              Confirm Settlement
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
