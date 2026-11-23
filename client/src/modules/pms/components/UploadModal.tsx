import { FileInput, Select, Stack, Text, TextInput } from "@mantine/core";
import { useState } from "react";

import { FormModal } from "../../../ui/components/FormModal";
import { useUploadDocument } from "../api/hooks";
import type { PmsDocument } from "../api/types";
import { SENSITIVITY_NAMES, words } from "./format";

const KINDS = ["specification", "claims", "drawings", "supporting", "filing_package",
  "office_action", "other"];

// BR-PMS-014..016: a PDF under 50 MB; the server checks the bytes and scans them.
export function UploadModal({ applicationId, existing, onClose }: {
  applicationId: number;
  existing: PmsDocument | null;
  onClose: () => void;
}) {
  const upload = useUploadDocument();
  const [file, setFile] = useState<File | null>(null);
  const [kind, setKind] = useState<string | null>("specification");
  const [title, setTitle] = useState("");
  const [sensitivity, setSensitivity] = useState<string | null>("confidential");
  const tooBig = file != null && file.size >= 50 * 1024 * 1024;
  const ready = file != null && !tooBig && (existing != null || (title.trim() && kind
    && sensitivity));

  return (
    <FormModal
      opened onClose={onClose}
      title={existing ? `New version of "${existing.title}"` : "Upload a document"}
      subtitle="PDF only, under 50 MB. Every file is checked for malware before it is kept."
      submitLabel="Upload" submitting={upload.isPending} error={upload.error}
      disabled={!ready} disabledReason={tooBig ? "The file is 50 MB or larger."
        : file == null ? "Choose a file." : "Give it a title, a kind and a sensitivity."}
      onSubmit={() => file && upload.mutate({
        id: applicationId, file,
        ...(existing ? { document_id: existing.id } : { kind, title, sensitivity }),
      }, { onSuccess: onClose })}
    >
      <Stack gap="sm">
        <FileInput label="PDF file" required accept="application/pdf" value={file}
          onChange={setFile} placeholder="Choose a PDF" />
        {!existing && (
          <>
            <TextInput label="Title" required value={title}
              onChange={(e) => setTitle(e.currentTarget.value)} />
            <Select label="Kind" required allowDeselect={false} value={kind} onChange={setKind}
              data={KINDS.map((k) => ({ value: k, label: words(k) }))} />
            <Select label="Sensitivity" required allowDeselect={false} value={sensitivity} onChange={setSensitivity}
              data={Object.entries(SENSITIVITY_NAMES).map(([value, label]) => ({ value, label }))} />
            <Text size="xs" c="dimmed">
              Restricted documents are readable only by you, institute inventors, the assigned
              Director, the assigned Attorney and PCC_ADMIN.
            </Text>
          </>
        )}
      </Stack>
    </FormModal>
  );
}
