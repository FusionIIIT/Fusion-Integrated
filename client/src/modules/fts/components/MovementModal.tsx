import { useState } from "react";
import { Stack, TextInput, Textarea } from "@mantine/core";

import { useForwardFile, useReturnFile } from "../api/hooks";
import { FormModal } from "../../../ui/components/FormModal";
import { FtsError } from "./FtsError";

interface Props {
  fileId: number;
  mode: "forward" | "return";
  /** The employee's active role context (UC-008), sent as sender_role. */
  role: string;
  onClose: () => void;
}

/** Forward (also the first send of a draft) and Return. Both need a movement
 *  comment (BR-FTS-006); Forward also needs a receiver. */
export function MovementModal({ fileId, mode, role, onClose }: Props) {
  const forward = useForwardFile(fileId);
  const ret = useReturnFile(fileId);
  const [receiverId, setReceiverId] = useState("");
  const [receiverRole, setReceiverRole] = useState("");
  const [targetId, setTargetId] = useState("");
  const [comment, setComment] = useState("");

  const isForward = mode === "forward";
  const pending = isForward ? forward : ret;
  const missing = !comment.trim()
    ? "A movement comment is required."
    : isForward && !receiverId.trim() ? "Choose who to send the file to." : "";

  function submit() {
    if (missing) return;
    if (isForward) {
      forward.mutate(
        { receiver_id: receiverId.trim(), comment: comment.trim(),
          sender_role: role,
          // The backend rejects a blank role, so leave it out entirely.
          ...(receiverRole.trim() ? { receiver_role: receiverRole.trim() } : {}) },
        { onSuccess: onClose },
      );
    } else {
      ret.mutate(
        { comment: comment.trim(), sender_role: role,
          ...(targetId.trim() ? { target_receiver_id: targetId.trim() } : {}) },
        { onSuccess: onClose },
      );
    }
  }

  return (
    <FormModal
      opened onClose={onClose}
      title={isForward ? "Send / forward file" : "Return file"}
      subtitle={isForward
        ? "The recipient becomes the current holder."
        : "The file goes back to a previous sender."}
      submitLabel={isForward ? "Send" : "Return"}
      onSubmit={submit} submitting={pending.isPending}
      disabled={Boolean(missing)} disabledReason={missing}
      size="md"
    >
      <Stack gap="sm">
        {pending.error != null && <FtsError error={pending.error} />}
        {isForward ? (
          <>
            <TextInput
              label="Send to (employee ID)" required
              value={receiverId}
              onChange={(e) => setReceiverId(e.currentTarget.value)}
            />
            <TextInput
              label="Recipient's role (optional)"
              value={receiverRole}
              onChange={(e) => setReceiverRole(e.currentTarget.value)}
            />
          </>
        ) : (
          <TextInput
            label="Return to (employee ID, optional)"
            description="Leave blank to return to the previous sender."
            value={targetId}
            onChange={(e) => setTargetId(e.currentTarget.value)}
          />
        )}
        <Textarea
          label="Movement comment" required minRows={3} autosize
          value={comment}
          onChange={(e) => setComment(e.currentTarget.value)}
        />
      </Stack>
    </FormModal>
  );
}

export default MovementModal;
