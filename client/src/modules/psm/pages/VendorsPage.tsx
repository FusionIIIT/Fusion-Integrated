// Vendor onboarding, master data, and verification (PSM-UC-019, BR-PSM-012, BR-PSM-025).
import { useState } from "react";
import { Badge, Button, Card, Container, Stack, Text, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCreateVendor, useVendors, useVerifyVendor } from "../api/hooks";
import type { Vendor } from "../api/types";

export default function VendorsPage() {
  const { can } = useAuth();
  const { data, isPending, error } = useVendors();
  const createVendor = useCreateVendor();
  const verifyVendor = useVerifyVendor();

  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [gstin, setGstin] = useState("");
  const [bankAcct, setBankAcct] = useState("");
  const [bankIfsc, setBankIfsc] = useState("");
  const [bankName, setBankName] = useState("");
  const [docRef, setDocRef] = useState("");

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  return (
    <Container size="xl">
      <PageHeader
        title="Vendors"
        subtitle="Vendor onboarding, master data versioning, and verification"
        action={can("psm.vendor.create") ? <Button onClick={() => setCreating(true)}>Onboard vendor</Button> : undefined}
      />

      <Card padding="lg">
        <DataTable<Vendor>
          rows={data?.results ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          empty={{ title: "No vendors onboarded yet." }}
          columns={[
            {
              key: "name",
              header: "Vendor",
              render: (r) => (
                <Stack gap={0}>
                  <Text fw={600}>{r.name}</Text>
                  <Text size="xs" c="dimmed">{r.code} · v{r.version}</Text>
                </Stack>
              ),
            },
            { key: "gstin", header: "GSTIN", render: (r) => r.gstin || "—" },
            { key: "bank", header: "Bank", render: (r) => r.bank_name ? `${r.bank_name} (${r.bank_ifsc})` : "—" },
            {
              key: "verified",
              header: "Verification",
              render: (r) => <Badge color={r.is_verified ? "green" : "yellow"} variant="light">{r.is_verified ? "Verified" : "Unverified"}</Badge>,
            },
            {
              key: "actions",
              header: "Actions",
              align: "right",
              render: (r) =>
                can("psm.vendor.update") && !r.is_verified ? (
                  <Button
                    size="xs"
                    onClick={() =>
                      verifyVendor.mutate(r.id, {
                        onSuccess: () => notifications.show({ color: "green", title: "Verified", message: `${r.name} is now verified.` }),
                        onError: (e) => notifications.show({ color: "red", title: "Verification failed", message: errorMessage(e) }),
                      })
                    }
                  >
                    Verify
                  </Button>
                ) : (
                  <Text size="xs" c="dimmed">—</Text>
                ),
            },
          ]}
        />
      </Card>

      <FormModal
        opened={creating}
        onClose={() => setCreating(false)}
        title="Onboard Vendor"
        submitLabel="Save vendor"
        submitting={createVendor.isPending}
        onSubmit={() =>
          createVendor.mutate(
            {
              name,
              gstin,
              bank_account_number: bankAcct,
              bank_ifsc: bankIfsc,
              bank_name: bankName,
              compliance_documents: docRef ? [docRef] : [],
            },
            {
              onSuccess: () => {
                setCreating(false);
                setName("");
                notifications.show({ color: "green", title: "Onboarded", message: "Vendor saved as unverified." });
              },
              onError: (e) => notifications.show({ color: "red", title: "Could not onboard", message: errorMessage(e) }),
            },
          )
        }
      >
        <Stack gap="sm">
          <TextInput label="Vendor name" value={name} onChange={(e) => setName(e.currentTarget.value)} required />
          <TextInput label="GSTIN" value={gstin} onChange={(e) => setGstin(e.currentTarget.value)} />
          <TextInput label="Bank account number" value={bankAcct} onChange={(e) => setBankAcct(e.currentTarget.value)} />
          <TextInput label="Bank IFSC" value={bankIfsc} onChange={(e) => setBankIfsc(e.currentTarget.value)} />
          <TextInput label="Bank name" value={bankName} onChange={(e) => setBankName(e.currentTarget.value)} />
          <TextInput label="Compliance document reference" value={docRef} onChange={(e) => setDocRef(e.currentTarget.value)} />
        </Stack>
      </FormModal>
    </Container>
  );
}
