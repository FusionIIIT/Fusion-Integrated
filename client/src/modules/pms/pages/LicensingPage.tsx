import { useState } from "react";
import { Card, Container, Stack, Text } from "@mantine/core";

import { useAuth } from "../../../auth/AuthProvider";
import { DataTable, type Column } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useLicensingRequests } from "../api/hooks";
import type { LicensingRequest } from "../api/types";
import { PmsActionForm } from "../components/PmsActionForm";
import { PmsApplicationSelect } from "../components/PmsApplicationSelect";

export default function LicensingPage() {
  const { can } = useAuth();
  const [selected, setSelected] = useState<string | null>(null);
  const requests = useLicensingRequests(selected ? Number(selected) : undefined);
  const columns: Column<LicensingRequest>[] = [
    { key: "licensee_name", header: "Licensee" },
    { key: "request_type", header: "Request" },
    { key: "status", header: "Status", render: (row) => <StatusBadge status={row.status} /> },
    { key: "created_at", header: "Submitted" },
  ];

  return (
    <Container size="xl">
      <PageHeader title="Licensing and technology transfer" subtitle="Submit a request or review records visible for an authorized application." />
      <Card padding="lg"><PmsApplicationSelect value={selected} onChange={setSelected} /></Card>
      {requests.error && <Card mt="md"><ErrorState error={requests.error} /></Card>}
      {selected && can("pms.licensing.submit") && (
        <Card padding="lg" mt="md">
          <PmsActionForm
            title="Submit licensing request"
            path={() => `/applications/${selected}/licensing/`}
            fields={[
              { name: "licensee_name", label: "Licensee name", required: true },
              { name: "request_type", label: "Request type", required: true },
              { name: "commercial_terms", label: "Commercial terms", type: "textarea", required: true },
            ]}
            submitLabel="Submit request"
            successTitle="Licensing request submitted"
          />
        </Card>
      )}
      {selected && (
        <Card padding="lg" mt="md">
          <PageHeader title="Licensing requests" />
          <DataTable rows={requests.data ?? []} columns={columns} rowKey={(row) => row.id}
            loading={requests.isPending} minWidth={700}
            empty={{ title: "No licensing requests", description: "Requests submitted for this application will appear here." }} />
          {can("pms.licensing.review") && (requests.data ?? []).map((request) => (
            <Card key={request.id} withBorder padding="md" mt="sm">
              <Stack gap="sm">
                <PageHeader title={`${request.licensee_name} · ${request.request_type}`}
                  subtitle={request.commercial_terms}
                  action={<StatusBadge status={request.status} />} />
                <PmsActionForm
                  title="Review request"
                  path={() => `/licensing/${request.id}/review/`}
                  fields={[
                    { name: "status", label: "Outcome", type: "select", required: true, options: [
                      { value: "under_review", label: "Under review" },
                      { value: "negotiating", label: "Negotiating" },
                      { value: "agreement_recorded", label: "Agreement recorded" },
                      { value: "rejected", label: "Rejected" },
                    ] },
                    { name: "negotiation_notes", label: "Negotiation notes", type: "textarea" },
                    { name: "agreement_reference", label: "Agreement reference" },
                  ]}
                  transform={(body) => Object.fromEntries(
                    Object.entries(body).filter(([, value]) => value !== ""),
                  )}
                  submitLabel="Record review"
                />
              </Stack>
            </Card>
          ))}
        </Card>
      )}
      {!selected && <Text c="dimmed" mt="md">Choose an application to load its requests.</Text>}
    </Container>
  );
}
