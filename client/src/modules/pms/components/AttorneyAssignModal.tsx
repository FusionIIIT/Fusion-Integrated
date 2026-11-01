import { useState } from "react";
import { Select, Stack, Text, Textarea } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { FormModal } from "../../../ui/components/FormModal";
import { useAssignAttorney, useAttorneyPanels } from "../api/hooks";

export function AttorneyAssignModal({
  applicationId,
  opened,
  onClose,
}: {
  applicationId: number | null;
  opened: boolean;
  onClose: () => void;
}) {
  const { data: panelsData, isPending: panelsLoading } = useAttorneyPanels();
  const [attorneyId, setAttorneyId] = useState<string | null>(null);
  const [instructions, setInstructions] = useState<string>("");
  const assignMutation = useAssignAttorney(applicationId ?? 0);

  const activePanels = panelsData?.results?.filter((p) => p.is_active) ?? [];

  const handleSubmit = async () => {
    if (!applicationId || !attorneyId) return;

    try {
      await assignMutation.mutateAsync({
        attorney_user_id: Number(attorneyId),
        instructions: instructions.trim(),
      });
      notifications.show({
        color: "green",
        message: "Attorney assignment offered successfully (BR-PMS-021).",
      });
      setAttorneyId(null);
      setInstructions("");
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
      title="Offer Attorney Assignment"
      onSubmit={handleSubmit}
      submitLabel="Send Assignment Offer"
      submitting={assignMutation.isPending}
      disabled={!attorneyId}
      disabledReason={!attorneyId ? "Please select an attorney" : undefined}
    >
      <Stack gap="md">
        <Select
          label="Empaneled Patent Attorney"
          description="Select attorney from approved institutional panel"
          placeholder={panelsLoading ? "Loading panel..." : "Select attorney"}
          value={attorneyId}
          onChange={setAttorneyId}
          data={activePanels.map((p) => ({
            value: String(p.user_id),
            label: `${p.name} (${p.firm_name}) - ${p.specialization} [Load: ${p.current_workload}/${p.max_workload}]`,
          }))}
          required
          searchable
        />

        <Textarea
          label="Special Instructions & Filing Priorities"
          placeholder="E.g. Expedited examination, jurisdiction focus, priority deadlines..."
          minRows={3}
          value={instructions}
          onChange={(e) => setInstructions(e.target.value)}
        />

        <Text size="xs" c="dimmed">
          Attorney will receive an assignment offer and must accept or decline with conflict-of-interest verification.
        </Text>
      </Stack>
    </FormModal>
  );
}
