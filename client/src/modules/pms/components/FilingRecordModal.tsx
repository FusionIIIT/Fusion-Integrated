import { useState } from "react";
import { Select, Stack, TextInput, Textarea } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { FormModal } from "../../../ui/components/FormModal";
import { useRecordFiling } from "../api/hooks";

export function FilingRecordModal({
  applicationId,
  opened,
  onClose,
}: {
  applicationId: number | null;
  opened: boolean;
  onClose: () => void;
}) {
  const [jurisdiction, setJurisdiction] = useState<string>("IN");
  const [filingNumber, setFilingNumber] = useState<string>("");
  const [filingDate, setFilingDate] = useState<string>(
    new Date().toISOString().split("T")[0] || ""
  );
  const [patentOffice, setPatentOffice] = useState<string>("Indian Patent Office (IPO)");
  const [confirmationDetails, setConfirmationDetails] = useState<string>("");
  const [intlJustification, setIntlJustification] = useState<string>("");

  const filingMutation = useRecordFiling(applicationId ?? 0);

  const handleSubmit = async () => {
    if (!applicationId || !filingNumber.trim()) return;

    try {
      await filingMutation.mutateAsync({
        jurisdiction,
        filing_number: filingNumber.trim(),
        filing_date: filingDate,
        patent_office: patentOffice.trim(),
        confirmation_details: confirmationDetails.trim(),
        international_justification: intlJustification.trim(),
      });
      notifications.show({
        color: "green",
        message: "External filing recorded successfully (BR-PMS-031).",
      });
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
      title="Record Official Patent Filing"
      onSubmit={handleSubmit}
      submitLabel="Confirm Official Filing"
      submitting={filingMutation.isPending}
      disabled={!filingNumber.trim()}
      disabledReason={!filingNumber.trim() ? "Filing number is required" : undefined}
    >
      <Stack gap="md">
        <Select
          label="Filing Jurisdiction"
          value={jurisdiction}
          onChange={(val) => setJurisdiction(val ?? "IN")}
          data={[
            { value: "IN", label: "India (IPO)" },
            { value: "US", label: "United States (USPTO)" },
            { value: "EP", label: "European Patent Office (EPO)" },
            { value: "PCT", label: "WIPO / PCT International" },
          ]}
          required
        />

        <TextInput
          label="Official Patent Application Number / CBR Number"
          placeholder="E.g. 202611004592"
          value={filingNumber}
          onChange={(e) => setFilingNumber(e.target.value)}
          required
        />

        <TextInput
          label="Official Filing Date"
          type="date"
          value={filingDate}
          onChange={(e) => setFilingDate(e.target.value)}
          required
        />

        <TextInput
          label="Receiving Patent Office Branch"
          value={patentOffice}
          onChange={(e) => setPatentOffice(e.target.value)}
          required
        />

        {jurisdiction !== "IN" && (
          <Textarea
            label="Foreign Filing License / Justification"
            placeholder="State Section 39 clearance or foreign filing justification..."
            value={intlJustification}
            onChange={(e) => setIntlJustification(e.target.value)}
            required
          />
        )}

        <Textarea
          label="CBR Details / Filing Receipt Remarks"
          placeholder="Payment reference, receipt token, filing attorney notes..."
          value={confirmationDetails}
          onChange={(e) => setConfirmationDetails(e.target.value)}
        />
      </Stack>
    </FormModal>
  );
}
