import React, { useState } from "react";
import {
  ActionIcon,
  Badge,
  Button,
  Card,
  Group,
  Modal,
  Stack,
  Table,
  Text,
  TextInput,
  Tooltip,
} from "@mantine/core";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useVendors, useCreateVendor, useVerifyVendor } from "../api/hooks";
import type { Vendor } from "../api/types";
import { errorMessage } from "../../../lib/http";

export default function VendorsPage() {
  const [searchTerm, setSearchTerm] = useState("");
  const [modalOpened, setModalOpened] = useState(false);

  // Form state
  const [name, setName] = useState("");
  const [gstNumber, setGstNumber] = useState("");
  const [bankAccount, setBankAccount] = useState("");
  const [bankIfsc, setBankIfsc] = useState("");
  const [complianceUrl, setComplianceUrl] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const { data: vendors = [], isLoading, refetch } = useVendors();
  const createVendorMutation = useCreateVendor();
  const verifyVendorMutation = useVerifyVendor(0);

  const handleCreateVendor = async () => {
    setFormError(null);
    if (!name.trim()) {
      setFormError("Vendor name is required.");
      return;
    }
    const gstClean = gstNumber.trim().toUpperCase();
    if (gstClean.length !== 15) {
      setFormError("GST number must be exactly 15 alphanumeric characters.");
      return;
    }
    if (!bankAccount.trim()) {
      setFormError("Bank account number is required.");
      return;
    }
    if (!bankIfsc.trim()) {
      setFormError("Bank IFSC is required.");
      return;
    }

    try {
      await createVendorMutation.mutateAsync({
        name: name.trim(),
        gst_number: gstClean,
        bank_account_number: bankAccount.trim(),
        bank_ifsc: bankIfsc.trim().toUpperCase(),
        compliance_docs_url: complianceUrl.trim(),
      });
      setModalOpened(false);
      setName("");
      setGstNumber("");
      setBankAccount("");
      setBankIfsc("");
      setComplianceUrl("");
      refetch();
    } catch (e: unknown) {
      setFormError(errorMessage(e));
    }
  };

  const handleVerify = async (vendorId: number) => {
    try {
      await verifyVendorMutation.mutateAsync();
      refetch();
    } catch (e: unknown) {
      alert(errorMessage(e));
    }
  };

  const filteredVendors = vendors.filter((v: Vendor) =>
    v.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    v.gst_number.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <Stack gap="lg" p="md">
      <PageHeader
        title="Vendor Directory"
        subtitle="Manage supplier compliance, verification gates, and GST records."
        action={
          <Button onClick={() => setModalOpened(true)} color="blue">
            + Register Vendor
          </Button>
        }
      />

      <Card withBorder radius="md" p="md">
        <TextInput
          placeholder="Search by vendor name or GST number..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.currentTarget.value)}
          mb="md"
        />

        <Table striped highlightOnHover verticalSpacing="sm" horizontalSpacing="md">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Vendor Name</Table.Th>
              <Table.Th>GST Number</Table.Th>
              <Table.Th>Bank Details</Table.Th>
              <Table.Th>Verification Status</Table.Th>
              <Table.Th>Compliance Docs</Table.Th>
              <Table.Th style={{ textAlign: "right" }}>Actions</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {isLoading ? (
              <Table.Tr>
                <Table.Td colSpan={6} style={{ textAlign: "center", padding: "2rem" }}>
                  Loading Vendors...
                </Table.Td>
              </Table.Tr>
            ) : filteredVendors.length === 0 ? (
              <Table.Tr>
                <Table.Td colSpan={6} style={{ textAlign: "center", padding: "2rem", color: "#888" }}>
                  No vendors registered.
                </Table.Td>
              </Table.Tr>
            ) : (
              filteredVendors.map((vendor: Vendor) => (
                <Table.Tr key={vendor.id}>
                  <Table.Td>
                    <Text fw={600} size="sm">{vendor.name}</Text>
                    <Text size="xs" c="dimmed">Version: v{vendor.version}</Text>
                  </Table.Td>
                  <Table.Td>
                    <Text size="sm" ff="monospace">{vendor.gst_number}</Text>
                  </Table.Td>
                  <Table.Td>
                    <Text size="xs">A/C: {vendor.bank_account_number}</Text>
                    <Text size="xs" c="dimmed">IFSC: {vendor.bank_ifsc}</Text>
                  </Table.Td>
                  <Table.Td>
                    {vendor.is_verified ? (
                      <Badge color="green" variant="filled">VERIFIED</Badge>
                    ) : (
                      <Badge color="yellow" variant="light">PENDING VERIFICATION</Badge>
                    )}
                  </Table.Td>
                  <Table.Td>
                    {vendor.compliance_docs_url ? (
                      <a href={vendor.compliance_docs_url} target="_blank" rel="noreferrer" style={{ fontSize: "0.85rem", color: "#0066cc" }}>
                        View Documents
                      </a>
                    ) : (
                      <Text size="xs" c="dimmed">None attached</Text>
                    )}
                  </Table.Td>
                  <Table.Td style={{ textAlign: "right" }}>
                    {!vendor.is_verified && (
                      <Button
                        size="xs"
                        color="teal"
                        onClick={() => handleVerify(vendor.id)}
                      >
                        Verify Vendor
                      </Button>
                    )}
                  </Table.Td>
                </Table.Tr>
              ))
            )}
          </Table.Tbody>
        </Table>
      </Card>

      {/* Register Vendor Modal */}
      <Modal
        opened={modalOpened}
        onClose={() => setModalOpened(false)}
        title="Register New Vendor"
        size="md"
        centered
      >
        <Stack gap="md">
          {formError && (
            <Text c="red" size="sm">{formError}</Text>
          )}

          <TextInput
            label="Vendor / Firm Name"
            placeholder="E.g., Global Tech Solutions Pvt. Ltd."
            value={name}
            onChange={(e) => setName(e.currentTarget.value)}
            required
          />

          <TextInput
            label="GST Identification Number (GSTIN)"
            placeholder="22AAAAA0000A1Z5"
            value={gstNumber}
            onChange={(e) => setGstNumber(e.currentTarget.value)}
            required
            maxLength={15}
          />

          <TextInput
            label="Bank Account Number"
            placeholder="Account number for direct disbursement"
            value={bankAccount}
            onChange={(e) => setBankAccount(e.currentTarget.value)}
            required
          />

          <TextInput
            label="Bank IFSC Code"
            placeholder="SBIN0001234"
            value={bankIfsc}
            onChange={(e) => setBankIfsc(e.currentTarget.value)}
            required
          />

          <TextInput
            label="Compliance Documents Link / URL (Optional)"
            placeholder="https://drive.google.com/..."
            value={complianceUrl}
            onChange={(e) => setComplianceUrl(e.currentTarget.value)}
          />

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setModalOpened(false)}>Cancel</Button>
            <Button color="blue" onClick={handleCreateVendor} loading={createVendorMutation.isPending}>
              Register Vendor
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}
