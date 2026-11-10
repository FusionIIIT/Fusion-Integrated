import React, { useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  Group,
  Modal,
  NumberInput,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Textarea,
} from "@mantine/core";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  usePurchaseOrders,
  useVendors,
  useIndents,
  useCreatePurchaseOrder,
  useRecordGRN,
} from "../api/hooks";
import type { PurchaseOrder, Vendor, Indent } from "../api/types";
import { errorMessage } from "../../../lib/http";

export default function PurchaseOrdersPage() {
  const [modalOpened, setModalOpened] = useState(false);
  const [grnModalOpened, setGrnModalOpened] = useState(false);
  const [selectedPoForGrn, setSelectedPoForGrn] = useState<PurchaseOrder | null>(null);

  // PO form state
  const [selectedIndentId, setSelectedIndentId] = useState<string | null>(null);
  const [selectedVendorId, setSelectedVendorId] = useState<string | null>(null);
  const [procurementMethod, setProcurementMethod] = useState<"DIRECT" | "TENDER">("DIRECT");
  const [totalCost, setTotalCost] = useState("");
  const [deliverySchedule, setDeliverySchedule] = useState("");
  const [poError, setPoError] = useState<string | null>(null);

  // GRN form state
  const [acceptedQty, setAcceptedQty] = useState<number | string>(1);
  const [rejectedQty, setRejectedQty] = useState<number | string>(0);
  const [inspectionRemarks, setInspectionRemarks] = useState("");
  const [grnError, setGrnError] = useState<string | null>(null);

  const { data: pos = [], isLoading, refetch: refetchPos } = usePurchaseOrders();
  const { data: vendors = [] } = useVendors();
  const { data: indents = [] } = useIndents();

  const createPoMutation = useCreatePurchaseOrder();
  const recordGrnMutation = useRecordGRN();

  const approvedIndents = indents.filter((ind: Indent) =>
    ["APPROVED", "HEAD_RECOMMENDED", "AWAITING_FINAL_APPROVAL"].includes(ind.status)
  );

  const verifiedVendors = vendors.filter((v: Vendor) => v.is_verified);

  const handleCreatePO = async () => {
    setPoError(null);
    if (!selectedIndentId) {
      setPoError("Please select an approved indent.");
      return;
    }
    if (!selectedVendorId) {
      setPoError("Please select a verified vendor.");
      return;
    }

    // Verify vendor is verified
    const vendor = vendors.find((v) => v.id === Number(selectedVendorId));
    if (!vendor || !vendor.is_verified) {
      setPoError("Cannot create Purchase Order: Selected vendor is NOT verified.");
      return;
    }

    const costTrimmed = totalCost.trim();
    if (!costTrimmed || isNaN(Number(costTrimmed)) || Number(costTrimmed) <= 0) {
      setPoError("Total cost must be a valid positive amount.");
      return;
    }
    if (!deliverySchedule.trim()) {
      setPoError("Delivery schedule date is required (YYYY-MM-DD).");
      return;
    }

    try {
      await createPoMutation.mutateAsync({
        indent_id: Number(selectedIndentId),
        vendor_id: Number(selectedVendorId),
        procurement_method: procurementMethod,
        total_cost: costTrimmed,
        delivery_schedule: deliverySchedule.trim(),
      });
      setModalOpened(false);
      setSelectedIndentId(null);
      setSelectedVendorId(null);
      setTotalCost("");
      setDeliverySchedule("");
      refetchPos();
    } catch (e: unknown) {
      setPoError(errorMessage(e));
    }
  };

  const handleRecordGRN = async () => {
    setGrnError(null);
    if (!selectedPoForGrn) return;

    const acc = Number(acceptedQty);
    const rej = Number(rejectedQty);
    if (acc < 0 || rej < 0) {
      setGrnError("Quantities cannot be negative.");
      return;
    }
    if (acc === 0 && rej === 0) {
      setGrnError("At least one item must be received.");
      return;
    }

    try {
      await recordGrnMutation.mutateAsync({
        purchase_order_id: selectedPoForGrn.id,
        accepted_quantity: acc,
        rejected_quantity: rej,
        inspection_remarks: inspectionRemarks.trim(),
      });
      setGrnModalOpened(false);
      setSelectedPoForGrn(null);
      setAcceptedQty(1);
      setRejectedQty(0);
      setInspectionRemarks("");
      refetchPos();
    } catch (e: unknown) {
      setGrnError(errorMessage(e));
    }
  };

  return (
    <Stack gap="lg" p="md">
      <PageHeader
        title="Purchase Orders & Goods Receipt"
        subtitle="Manage formal procurement contracts, vendor issuance, and delivery receipts."
        action={
          <Button onClick={() => setModalOpened(true)} color="blue">
            + Issue Purchase Order
          </Button>
        }
      />

      <Card withBorder radius="md" p={0}>
        <Table striped highlightOnHover verticalSpacing="sm" horizontalSpacing="md">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>PO Number</Table.Th>
              <Table.Th>Indent ID</Table.Th>
              <Table.Th>Vendor</Table.Th>
              <Table.Th>Method</Table.Th>
              <Table.Th>Total Value (INR)</Table.Th>
              <Table.Th>Delivery Due</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th style={{ textAlign: "right" }}>Actions</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {isLoading ? (
              <Table.Tr>
                <Table.Td colSpan={8} style={{ textAlign: "center", padding: "2rem" }}>
                  Loading Purchase Orders...
                </Table.Td>
              </Table.Tr>
            ) : pos.length === 0 ? (
              <Table.Tr>
                <Table.Td colSpan={8} style={{ textAlign: "center", padding: "2rem", color: "#888" }}>
                  No Purchase Orders issued yet.
                </Table.Td>
              </Table.Tr>
            ) : (
              pos.map((po: PurchaseOrder) => (
                <Table.Tr key={po.id}>
                  <Table.Td>
                    <Text fw={600} size="sm">{po.po_number}</Text>
                  </Table.Td>
                  <Table.Td>
                    <Text size="sm">{po.indent_business_id || `#${po.indent}`}</Text>
                  </Table.Td>
                  <Table.Td>
                    <Text size="sm">{po.vendor_name || `Vendor #${po.vendor}`}</Text>
                  </Table.Td>
                  <Table.Td>
                    <Badge color={po.procurement_method === "TENDER" ? "grape" : "cyan"} variant="light">
                      {po.procurement_method}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Text fw={600}>₹{Number(po.total_cost).toLocaleString("en-IN")}</Text>
                  </Table.Td>
                  <Table.Td>{po.delivery_schedule}</Table.Td>
                  <Table.Td>
                    <Badge
                      color={
                        po.status === "DELIVERED"
                          ? "green"
                          : po.status === "CANCELLED"
                          ? "red"
                          : "blue"
                      }
                      variant="filled"
                    >
                      {po.status}
                    </Badge>
                  </Table.Td>
                  <Table.Td style={{ textAlign: "right" }}>
                    {po.status === "ISSUED" && (
                      <Button
                        size="xs"
                        color="teal"
                        onClick={() => {
                          setSelectedPoForGrn(po);
                          setAcceptedQty(1);
                          setRejectedQty(0);
                          setInspectionRemarks("");
                          setGrnModalOpened(true);
                        }}
                      >
                        Record GRN
                      </Button>
                    )}
                  </Table.Td>
                </Table.Tr>
              ))
            )}
          </Table.Tbody>
        </Table>
      </Card>

      {/* Issue PO Modal */}
      <Modal
        opened={modalOpened}
        onClose={() => setModalOpened(false)}
        title="Issue Purchase Order"
        size="lg"
        centered
      >
        <Stack gap="md">
          {poError && (
            <Alert color="red" title="Validation Error">
              {poError}
            </Alert>
          )}

          <Select
            label="Select Approved Requisition / Indent"
            placeholder="Select indent..."
            data={approvedIndents.map((ind: Indent) => ({
              value: String(ind.id),
              label: `${ind.indent_id} - ${ind.item_details.slice(0, 40)} (₹${ind.estimated_cost})`,
            }))}
            value={selectedIndentId}
            onChange={(val) => {
              setSelectedIndentId(val);
              const found = approvedIndents.find((i) => String(i.id) === val);
              if (found) {
                setTotalCost(found.estimated_cost);
                setProcurementMethod(Number(found.estimated_cost) >= 100000 ? "TENDER" : "DIRECT");
              }
            }}
            required
          />

          <Select
            label="Select Verified Vendor"
            placeholder="Select vendor..."
            data={verifiedVendors.map((v: Vendor) => ({
              value: String(v.id),
              label: `${v.name} (GST: ${v.gst_number})`,
            }))}
            value={selectedVendorId}
            onChange={setSelectedVendorId}
            required
            description={
              verifiedVendors.length === 0
                ? "No verified vendors available. Please verify vendors in Vendor Directory first."
                : "Only verified vendors are compliant for Purchase Order issuance."
            }
          />

          <Select
            label="Procurement Method"
            data={[
              { value: "DIRECT", label: "Direct Purchase (< ₹1,00,000)" },
              { value: "TENDER", label: "Tender / Bidding Process (>= ₹1,00,000)" },
            ]}
            value={procurementMethod}
            onChange={(val) => setProcurementMethod((val as "DIRECT" | "TENDER") || "DIRECT")}
            required
          />

          <TextInput
            label="Total Purchase Order Amount (INR)"
            placeholder="e.g. 50000.00"
            value={totalCost}
            onChange={(e) => setTotalCost(e.currentTarget.value)}
            required
          />

          <TextInput
            label="Delivery Schedule Date"
            placeholder="YYYY-MM-DD"
            value={deliverySchedule}
            onChange={(e) => setDeliverySchedule(e.currentTarget.value)}
            required
          />

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setModalOpened(false)}>Cancel</Button>
            <Button color="blue" onClick={handleCreatePO} loading={createPoMutation.isPending}>
              Issue Purchase Order
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Record GRN Modal */}
      <Modal
        opened={grnModalOpened}
        onClose={() => setGrnModalOpened(false)}
        title={`Record Goods Receipt Note (GRN) — ${selectedPoForGrn?.po_number || ""}`}
        size="md"
        centered
      >
        <Stack gap="md">
          {grnError && (
            <Alert color="red" title="Error">
              {grnError}
            </Alert>
          )}

          <NumberInput
            label="Accepted / Conforming Quantity"
            placeholder="0"
            value={acceptedQty}
            onChange={(val) => setAcceptedQty(val)}
            min={0}
            required
          />

          <NumberInput
            label="Rejected / Defective Quantity"
            placeholder="0"
            value={rejectedQty}
            onChange={(val) => setRejectedQty(val)}
            min={0}
          />

          <Textarea
            label="Inspection Remarks"
            placeholder="Condition of packaging, serial numbers, quality verification notes..."
            value={inspectionRemarks}
            onChange={(e) => setInspectionRemarks(e.currentTarget.value)}
            minRows={2}
          />

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setGrnModalOpened(false)}>Cancel</Button>
            <Button color="teal" onClick={handleRecordGRN} loading={recordGrnMutation.isPending}>
              Confirm Goods Receipt
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}
