import { useState } from "react";
import { Stack, Text, Textarea } from "@mantine/core";

import { useArchiveFile } from "../api/hooks";
import { FormModal } from "../../../ui/components/FormModal";
import { FtsError } from "./FtsError";

/** Archiving is permanent: the file becomes read-only (BR-FTS-012). */
export function ArchiveModal({ fileId, role, onClose }: {
  fileId: number; role: string; onClose: () => void;
}) {
  const archive = useArchiveFile(fileId);
  const [remarks, setRemarks] = useState("");
  const missing = remarks.trim() ? "" : "Closing remarks are required.";

  function submit() {
    if (missing) return;
    archive.mutate({ remarks: remarks.trim(), user_role: role },
      { onSuccess: onClose });
  }

  return (
    <FormModal
      opened onClose={onClose} title="Archive file"
      subtitle="An archived file is read-only and cannot be forwarded again."
      submitLabel="Archive" danger size="md"
      onSubmit={submit} submitting={archive.isPending}
      disabled={Boolean(missing)} disabledReason={missing}
    >
      <Stack gap="sm">
        {archive.error != null && <FtsError error={archive.error} />}
        <Text size="sm">This cannot be undone.</Text>
        <Textarea
          label="Closing remarks" required minRows={3} autosize
          value={remarks}
          onChange={(e) => setRemarks(e.currentTarget.value)}
        />
      </Stack>
    </FormModal>
  );
}

export default ArchiveModal;
