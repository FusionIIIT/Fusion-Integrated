import { Button, Stack } from "@mantine/core";
import { FaCheckCircle } from "react-icons/fa";
import { DataTable, type Column } from "../../../ui/components/DataTable";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useVendors, useVerifyVendor } from "../api/hooks";
import type { Vendor } from "../api/types";

export default function VendorsPage() {
  const { data: vendors = [], isLoading } = useVendors();
  const verifyVendor = useVerifyVendor();

  const handleVerify = async (id: number) => {
    await verifyVendor.mutateAsync(id);
  };

  const columns: Column<Vendor>[] = [
    { key: "vendor_code", header: "Vendor Code" },
    { key: "name", header: "Supplier Name" },
    { key: "contact_person", header: "Contact Person" },
    { key: "email", header: "Email" },
    { key: "phone", header: "Phone" },
    {
      key: "status",
      header: "Status",
      render: (r) => <StatusBadge status={r.status.toLowerCase()} />,
    },
    {
      key: "actions",
      header: "Actions",
      align: "right",
      render: (r) =>
        r.status !== "VERIFIED" ? (
          <Button
            size="xs"
            color="green"
            variant="light"
            leftSection={<FaCheckCircle size={12} />}
            onClick={() => handleVerify(r.id)}
            loading={verifyVendor.isPending}
          >
            Verify Vendor
          </Button>
        ) : null,
    },
  ];

  return (
    <Stack gap="lg">
      <PageHeader
        title="Vendor Master Directory"
        subtitle="Manage approved suppliers, compliance verification, and banking records"
      />
      <DataTable
        rows={vendors}
        columns={columns}
        loading={isLoading}
        rowKey={(r) => r.id}
        empty={{
          title: "No vendor records found",
          description: "Vendors onboarded for procurement orders will be indexed here.",
        }}
      />
    </Stack>
  );
}
