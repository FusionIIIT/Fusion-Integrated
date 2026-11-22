import { Card, Container } from "@mantine/core";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useSecurityPolicies } from "../api/hooks";
import type { SecurityPolicy } from "../api/types";

export default function SecurityPoliciesPage() {
  const { data, isPending, error } = useSecurityPolicies();

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  return (
    <Container size="xl">
      <PageHeader
        title="Security & Encryption Policies"
        subtitle="Manage classification-based encryption standards and dual-authorization policies"
      />
      <Card padding="lg">
        <DataTable<SecurityPolicy>
          rows={data?.results ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={800}
          empty={{ title: "No security policies", description: "No security policies configured." }}
          columns={[
            { key: "id", header: "ID", render: (r) => r.id },
            {
              key: "policy_key",
              header: "Policy Key",
              render: (r) => r.policy_key,
            },
            {
              key: "status",
              header: "Status",
              render: (r) => <StatusBadge status={r.is_active ? "active" : "closed"} />,
            },
            {
              key: "effective_from",
              header: "Effective From",
              render: (r) => new Date(r.effective_from).toLocaleDateString(),
            },
            {
              key: "created_at",
              header: "Configured At",
              render: (r) => new Date(r.created_at).toLocaleString(),
            },
          ]}
        />
      </Card>
    </Container>
  );
}
