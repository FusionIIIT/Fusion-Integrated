import { useState } from "react";
import {
  Button,
  Container,
  Group,
  Stack,
  Tabs,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { DataTable, type Column } from "../../../ui/components/DataTable";
import { StatusBadge } from "../components/StatusBadge";
import { DecisionModal } from "../components/DecisionModal";
import { useRequests, useTravelClaims, useDecideRequest } from "../api/hooks";
import type { ExpenseVoucherRequest, TAClaim } from "../api/types";

export default function ApprovalsPage() {
  const { data: requests, isPending: reqPending, error: reqError } = useRequests();
  const { data: claims, isPending: claimsPending, error: claimsError } = useTravelClaims();
  const decideMutation = useDecideRequest();
  const { can } = useAuth();

  const [activeTab, setActiveTab] = useState<string | null>("requests");
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedRequest, setSelectedRequest] = useState<ExpenseVoucherRequest | null>(null);
  const [decision, setDecision] = useState<"approve" | "reject">("approve");

  const canApprove = can("iaa.request.approve");

  if (reqError || claimsError) {
    return (
      <Container size="xl">
        <ErrorState error={reqError || claimsError} />
      </Container>
    );
  }

  const pendingRequests = (requests || []).filter((r) =>
    ["finance_validated", "approval_pending", "escalated"].includes(r.status)
  );

  const pendingClaims = (claims || []).filter((c) =>
    ["approval_pending", "escalated"].includes(c.status)
  );

  const handleOpenDecision = (req: ExpenseVoucherRequest, type: "approve" | "reject") => {
    setSelectedRequest(req);
    setDecision(type);
    setModalOpen(true);
  };

  const handleConfirmDecision = async (remarks: string) => {
    if (!selectedRequest) return;
    await decideMutation.mutateAsync({
      id: selectedRequest.id,
      decision,
      remarks,
    });
    notifications.show({
      title: "Decision Recorded",
      message: `Request #${selectedRequest.id} was ${decision}d.`,
      color: decision === "approve" ? "green" : "red",
    });
  };

  const requestColumns: Column<ExpenseVoucherRequest>[] = [
    { key: "id", header: "ID", render: (r) => `#${r.id}` },
    { key: "title", header: "Title", render: (r) => r.title },
    { key: "department", header: "Department", render: (r) => r.department },
    { key: "total_amount", header: "Amount", render: (r) => `₹${r.total_amount}` },
    {
      key: "level",
      header: "Level",
      render: (r) => `L${r.current_approval_level} of ${r.required_approval_levels}`,
    },
    { key: "status", header: "Status", render: (r) => <StatusBadge status={r.status} /> },
    {
      key: "actions",
      header: "Actions",
      render: (r) => (
        <Group gap="xs">
          {canApprove && (
            <>
              <Button size="xs" color="green" onClick={() => handleOpenDecision(r, "approve")}>
                Approve
              </Button>
              <Button size="xs" color="red" variant="outline" onClick={() => handleOpenDecision(r, "reject")}>
                Reject
              </Button>
            </>
          )}
        </Group>
      ),
    },
  ];

  const travelColumns: Column<TAClaim>[] = [
    { key: "id", header: "ID", render: (c) => `#TA-${c.id}` },
    { key: "purpose", header: "Purpose", render: (c) => c.purpose },
    { key: "department", header: "Department", render: (c) => c.department },
    { key: "claimed_amount", header: "Amount", render: (c) => `₹${c.claimed_amount}` },
    { key: "status", header: "Status", render: (c) => <StatusBadge status={c.status} /> },
  ];

  return (
    <Container size="xl">
      <Stack gap="lg">
        <PageHeader
          title="Approval Queue"
          subtitle="Review, approve, or reject pending expense vouchers and high-value travel claims."
        />

        <Tabs value={activeTab} onChange={setActiveTab}>
          <Tabs.List>
            <Tabs.Tab value="requests">Expense / Vouchers ({pendingRequests.length})</Tabs.Tab>
            <Tabs.Tab value="travel">High-Value Travel ({pendingClaims.length})</Tabs.Tab>
          </Tabs.List>

          <Tabs.Panel value="requests" pt="md">
            <DataTable
              rows={pendingRequests}
              columns={requestColumns}
              loading={reqPending}
              rowKey={(r) => r.id}
              empty={{ title: "No requests currently awaiting your approval." }}
            />
          </Tabs.Panel>

          <Tabs.Panel value="travel" pt="md">
            <DataTable
              rows={pendingClaims}
              columns={travelColumns}
              loading={claimsPending}
              rowKey={(c) => c.id}
              empty={{ title: "No high-value travel claims currently awaiting your approval." }}
            />
          </Tabs.Panel>
        </Tabs>

        {selectedRequest && (
          <DecisionModal
            opened={modalOpen}
            onClose={() => setModalOpen(false)}
            decision={decision}
            targetTitle={`Request #${selectedRequest.id}: ${selectedRequest.title}`}
            onConfirm={handleConfirmDecision}
          />
        )}
      </Stack>
    </Container>
  );
}
