import { useState } from "react";
import { Alert, Button, Group, Modal, Select, Stack, Textarea } from "@mantine/core";
import { errorMessage, useForwardFile, useRecipients, useReturnFile } from "../api/hooks";

interface MovementModalProps {
  opened: boolean;
  onClose: () => void;
  fileId: number;
  mode: "forward" | "return";
}

export const MovementModal: React.FC<MovementModalProps> = ({ opened, onClose, fileId, mode }) => {
  const forward = useForwardFile(fileId);
  const ret = useReturnFile(fileId);
  const { data: recipients } = useRecipients();

  const [recipient, setRecipient] = useState<string | null>(null);
  const [comment, setComment] = useState<string>("");
  const [problem, setProblem] = useState<string | null>(null);

  const handleSubmit = () => {
    if (comment.trim() === "") {
      setProblem("A comment is required");
      return;
    }

    if (mode === "forward" && recipient === null) {
      setProblem("Choose a recipient");
      return;
    }

    if (mode === "forward") {
      forward.mutate({ recipient_id: Number(recipient), comment }, { onSuccess: onClose });
    } else {
      ret.mutate({ comment }, { onSuccess: onClose });
    }
  };

  return (
    <Modal opened={opened} onClose={onClose} title="Movement">
      <Stack>
        {problem && <Alert color="red">{problem}</Alert>}
        {forward.isError || ret.isError && <Alert color="red">{errorMessage(forward.error ?? ret.error)}</Alert>}
        {mode === "forward" && (
          <Select
            label="Recipient"
            placeholder="Select a recipient"
            value={recipient}
            onChange={(value) => setRecipient(value)}
            data={(recipients ?? []).map(r => ({ value: String(r.id), label: `${r.name} (${r.designation})` }))}
          />
        )}
        <Textarea
          label="Comment"
          placeholder="Enter a comment"
          value={comment}
          onChange={(e) => setComment(e.target.value)}
        />
        <Group justify="flex-end">
          <Button type="submit" onClick={handleSubmit} loading={forward.isPending || ret.isPending}>
            Submit
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
};

export default MovementModal;
