import { useState } from "react";
import { Group, Stack, Text, TextInput, Textarea } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { FormModal } from "../../../ui/components/FormModal";
import { useApproveBudget } from "../api/hooks";

export function BudgetApprovalModal({
  applicationId,
  opened,
  onClose,
}: {
  applicationId: number | null;
  opened: boolean;
  onClose: () => void;
}) {
  const [filingFees, setFilingFees] = useState<string>("8000.00");
  const [attorneyFees, setAttorneyFees] = useState<string>("25000.00");
  const [adminCosts, setAdminCosts] = useState<string>("2000.00");
  const [justification, setJustification] = useState<string>("");

  const budgetMutation = useApproveBudget(applicationId ?? 0);

  const handleSubmit = async () => {
    if (!applicationId) return;

    try {
      await budgetMutation.mutateAsync({
        filing_fees: filingFees,
        attorney_fees: attorneyFees,
        administrative_costs: adminCosts,
        justification: justification.trim(),
      });
      notifications.show({
        color: "green",
        message: "Patent prosecution budget approved (BR-PMS-027).",
      });
      onClose();
    } catch (err) {
      notifications.show({
        color: "red",
        message: errorMessage(err),
      });
    }
  };

  const total = (
    (parseFloat(filingFees) || 0) +
    (parseFloat(attorneyFees) || 0) +
    (parseFloat(adminCosts) || 0)
  ).toFixed(2);

  return (
    <FormModal
      opened={opened}
      onClose={onClose}
      title="Prosecution Budget Approval"
      onSubmit={handleSubmit}
      submitLabel="Approve Budget"
      submitting={budgetMutation.isPending}
    >
      <Stack gap="md">
        <TextInput
          label="Government Filing Fees (INR)"
          value={filingFees}
          onChange={(e) => setFilingFees(e.target.value)}
          required
        />

        <TextInput
          label="Empaneled Attorney Fees (INR)"
          value={attorneyFees}
          onChange={(e) => setAttorneyFees(e.target.value)}
          required
        />

        <TextInput
          label="Administrative & Search Costs (INR)"
          value={adminCosts}
          onChange={(e) => setAdminCosts(e.target.value)}
          required
        />

        <Group justify="space-between" p="xs" style={{ background: "#f8f9fa", borderRadius: 4 }}>
          <Text fw={700} size="sm">
            Total Approved Budget:
          </Text>
          <Text fw={700} size="md" c="teal">
            ₹ {total}
          </Text>
        </Group>

        <Textarea
          label="Approval Remarks & Cost Center Justification"
          placeholder="Institute patent fund allocation reference..."
          value={justification}
          onChange={(e) => setJustification(e.target.value)}
        />
      </Stack>
    </FormModal>
  );
}
