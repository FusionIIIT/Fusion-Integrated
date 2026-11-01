import { useState } from "react";
import { Stack, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { FormModal } from "../../../ui/components/FormModal";
import { useRecordMaintenancePayment } from "../api/hooks";

export function MaintenancePaymentModal({
  scheduleId,
  feeAmount,
  cycleYear,
  opened,
  onClose,
}: {
  scheduleId: number | null;
  feeAmount: string;
  cycleYear: number;
  opened: boolean;
  onClose: () => void;
}) {
  const [paymentRef, setPaymentRef] = useState<string>("");
  const payMutation = useRecordMaintenancePayment(scheduleId ?? 0);

  const handleSubmit = async () => {
    if (!scheduleId || !paymentRef.trim()) return;

    try {
      await payMutation.mutateAsync({
        payment_reference: paymentRef.trim(),
        paid_amount: feeAmount,
      });
      notifications.show({
        color: "green",
        message: `Annuity fee for Year ${cycleYear} recorded successfully (BR-PMS-060).`,
      });
      setPaymentRef("");
      onClose();
    } catch (err) {
      notifications.show({
        color: "red",
        message: errorMessage(err),
      });
    }
  };

  return (
    <FormModal
      opened={opened}
      onClose={onClose}
      title={`Record Maintenance Fee Payment (Year ${cycleYear})`}
      onSubmit={handleSubmit}
      submitLabel="Record Annuity Payment"
      submitting={payMutation.isPending}
      disabled={!paymentRef.trim()}
      disabledReason={!paymentRef.trim() ? "Payment reference is required" : undefined}
    >
      <Stack gap="md">
        <TextInput
          label="Scheduled Statutory Annuity Fee (INR)"
          value={`₹ ${feeAmount}`}
          disabled
        />

        <TextInput
          label="Bank Transaction / Challan Reference Number"
          placeholder="E.g. IPO-CHALLAN-2026-90412"
          value={paymentRef}
          onChange={(e) => setPaymentRef(e.target.value)}
          required
        />
      </Stack>
    </FormModal>
  );
}
