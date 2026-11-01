import { Modal, Select, Textarea, Button, Group, Alert } from "@mantine/core";
import { useMutation } from "@tanstack/react-query";
import { useRecipients } from "../api/hooks";
import { useForwardFile, useReturnFile } from "../api/hooks";
import { errorMessage } from "../api/hooks";

interface MovementModalProps {
  opened: boolean;
  onClose: () => void;
  fileId: number;
  mode: "forward" | "return";
}

function MovementModal({ opened, onClose, fileId, mode }: MovementModalProps) {
  const { data: recipients } = useRecipients();
  const forwardMutation = useForwardFile();
  const returnMutation = useReturnFile();

  const [recipient, setRecipient] = useState<string | null>(null);
  const [comment, setComment] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!comment.trim()) {
      setError("A comment is required");
      return;
    }

    setError(null);

    if (mode === "forward") {
      if (!recipient) {
        setError("A recipient is required");
        return;
      }

      try {
        await forwardMutation.mutateAsync({ recipient_id: Number(recipient), comment });
        onClose();
      } catch (e) {
        setError(errorMessage(e));
      }
    } else if (mode === "return") {
      try {
        await returnMutation.mutateAsync({ comment });
        onClose();
      } catch (e) {
        setError(errorMessage(e));
      }
    }
  };

  return (
    <Modal opened={opened} onClose={onClose} title={mode === "forward" ? "Forward File" : "Return File"}>
      {error && <Alert color="red">{error}</Alert>}
      <form onSubmit={handleSubmit}>
        {mode === "forward" && (
          <Select
            label="Recipient"
            value={recipient}
            onChange={(value) => setRecipient(value)}
            data={recipients?.map((recipient) => ({ value: recipient.id.toString(), label: recipient.name })) || []}
            required
          />
        )}
        <Textarea
          label="Movement comment"
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          required
          error={error}
        />
        <Group position="right">
          <Button type="submit">Submit</Button>
        </Group>
      </form>
    </Modal>
  );
}

export { MovementModal };
export default MovementModal;
