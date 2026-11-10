import React, { useState } from "react";
import {
  Alert,
  NumberInput,
  Select,
  Stack,
  TextInput,
  Textarea,
} from "@mantine/core";
import { FormModal } from "../../../ui/components/FormModal";
import { useCreateIndent } from "../api/hooks";
import type { Priority } from "../api/types";
import { errorMessage } from "../../../lib/http";

interface CreateIndentModalProps {
  opened: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export function CreateIndentModal({ opened, onClose, onSuccess }: CreateIndentModalProps) {
  const [itemDetails, setItemDetails] = useState("");
  const [quantity, setQuantity] = useState<number | string>(1);
  const [estimatedCost, setEstimatedCost] = useState("");
  const [justification, setJustification] = useState("");
  const [priority, setPriority] = useState<Priority>("NORMAL");
  const [submitStatus, setSubmitStatus] = useState<"DRAFT" | "SUBMITTED">("SUBMITTED");
  const [clientError, setClientError] = useState<string | null>(null);

  const createIndentMutation = useCreateIndent();

  const resetForm = () => {
    setItemDetails("");
    setQuantity(1);
    setEstimatedCost("");
    setJustification("");
    setPriority("NORMAL");
    setSubmitStatus("SUBMITTED");
    setClientError(null);
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  const handleSubmit = async () => {
    setClientError(null);

    // Client-side validation
    if (!itemDetails.trim()) {
      setClientError("Item details are required.");
      return;
    }
    const qtyNum = Number(quantity);
    if (!qtyNum || qtyNum <= 0) {
      setClientError("Quantity must be a positive integer.");
      return;
    }
    const costTrimmed = estimatedCost.trim();
    if (!costTrimmed || isNaN(Number(costTrimmed)) || Number(costTrimmed) <= 0) {
      setClientError("Estimated cost must be a valid positive amount.");
      return;
    }
    if (!justification.trim()) {
      setClientError("Procurement justification is required.");
      return;
    }

    try {
      await createIndentMutation.mutateAsync({
        item_details: itemDetails.trim(),
        quantity: qtyNum,
        estimated_cost: costTrimmed,
        justification: justification.trim(),
        priority,
        status: submitStatus,
      });
      handleClose();
      onSuccess?.();
    } catch (e: unknown) {
      setClientError(errorMessage(e));
    }
  };

  return (
    <FormModal
      opened={opened}
      onClose={handleClose}
      title="Create Purchase Indent"
      subtitle="Submit a requisition for materials, equipment, or service procurement."
      submitLabel="Submit Indent"
      submitting={createIndentMutation.isPending}
      onSubmit={handleSubmit}
      size="lg"
    >
      <Stack gap="md">
        {clientError && (
          <Alert color="red" title="Validation Error">
            {clientError}
          </Alert>
        )}

        <Textarea
          label="Item Details & Specifications"
          placeholder="E.g., 27-inch 4K IPS monitors with HDMI & USB-C connectivity..."
          value={itemDetails}
          onChange={(e) => setItemDetails(e.currentTarget.value)}
          required
          minRows={3}
        />

        <NumberInput
          label="Requested Quantity"
          placeholder="1"
          value={quantity}
          onChange={(val) => setQuantity(val)}
          min={1}
          required
        />

        <TextInput
          label="Estimated Cost (INR)"
          placeholder="e.g. 50000.00"
          value={estimatedCost}
          onChange={(e) => setEstimatedCost(e.currentTarget.value)}
          description="Enter total estimated budget ceiling as a numeric monetary string."
          required
        />

        <Textarea
          label="Justification / Business Purpose"
          placeholder="Explain research requirement, project need, or departmental usage..."
          value={justification}
          onChange={(e) => setJustification(e.currentTarget.value)}
          required
          minRows={2}
        />

        <Select
          label="Requisition Priority"
          data={[
            { value: "NORMAL", label: "Normal Priority" },
            { value: "HIGH", label: "High Priority" },
            { value: "CRITICAL", label: "Critical (Emergency / Urgent)" },
          ]}
          value={priority}
          onChange={(val) => setPriority((val as Priority) || "NORMAL")}
          required
        />

        <Select
          label="Initial Status"
          data={[
            { value: "SUBMITTED", label: "Submit Immediately (Enters Verification)" },
            { value: "DRAFT", label: "Save as Draft (Editable Later)" },
          ]}
          value={submitStatus}
          onChange={(val) => setSubmitStatus((val as "DRAFT" | "SUBMITTED") || "SUBMITTED")}
          required
        />
      </Stack>
    </FormModal>
  );
}
