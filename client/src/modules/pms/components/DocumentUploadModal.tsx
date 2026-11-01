import { useState } from "react";
import { FileInput, Select, Stack, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { FormModal } from "../../../ui/components/FormModal";
import { useUploadDocument } from "../api/hooks";

export function DocumentUploadModal({
  applicationId,
  opened,
  onClose,
}: {
  applicationId: number | null;
  opened: boolean;
  onClose: () => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [docType, setDocType] = useState<string>("provisional_specification");
  const [title, setTitle] = useState<string>("");
  const [sensitivity, setSensitivity] = useState<string>("internal");

  const uploadMutation = useUploadDocument(applicationId ?? 0);

  const handleSubmit = async () => {
    if (!applicationId || !file) return;

    try {
      await uploadMutation.mutateAsync({
        file,
        document_type: docType,
        title: title.trim() || file.name,
        sensitivity,
      });
      notifications.show({
        color: "green",
        message: "Document uploaded and virus scanned successfully (BR-PMS-130).",
      });
      setFile(null);
      setTitle("");
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
      title="Upload Patent Document"
      onSubmit={handleSubmit}
      submitLabel="Upload Document"
      submitting={uploadMutation.isPending}
      disabled={!file}
      disabledReason={!file ? "Please select a file to upload" : undefined}
    >
      <Stack gap="md">
        <Select
          label="Document Classification"
          value={docType}
          onChange={(val) => setDocType(val ?? "provisional_specification")}
          data={[
            { value: "provisional_specification", label: "Provisional Specification" },
            { value: "complete_specification", label: "Complete Specification" },
            { value: "claims", label: "Claims Document" },
            { value: "drawings", label: "Technical Drawings" },
            { value: "abstract", label: "Patent Abstract" },
            { value: "prior_art", label: "Prior Art Reference / Non-Patent Literature" },
            { value: "inventor_consent", label: "Form 1 / Inventor Assignment & Consent" },
            { value: "power_of_attorney", label: "Form 26 / Power of Attorney" },
            { value: "other", label: "Other Supporting Document" },
          ]}
          required
        />

        <TextInput
          label="Document Title"
          placeholder="E.g. Complete Specification with Form 2"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />

        <Select
          label="Confidentiality & Access Sensitivity"
          value={sensitivity}
          onChange={(val) => setSensitivity(val ?? "internal")}
          data={[
            { value: "internal", label: "Internal Institute View" },
            { value: "confidential", label: "Confidential (Inventors & Assigned Attorney Only)" },
            { value: "public", label: "Public / Post-Publication Record" },
          ]}
          required
        />

        <FileInput
          label="Select File"
          placeholder="Choose PDF or DOCX file"
          value={file}
          onChange={setFile}
          accept=".pdf,.doc,.docx,.png,.jpg"
          required
        />
      </Stack>
    </FormModal>
  );
}
