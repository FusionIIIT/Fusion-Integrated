import { useState } from "react";
import { Button, Group, Modal, Stack, Text, Textarea } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { useFileAppeal } from "../api/hooks";

export function AppealModal({
  opened,
  onClose,
  applicationId,
  applicationTitle,
}: {
  opened: boolean;
  onClose: () => void;
  applicationId: number;
  applicationTitle: string;
}) {
  const [grounds, setGrounds] = useState("");
  const appeal = useFileAppeal(applicationId);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!grounds.trim()) {
      notifications.show({
        color: "red",
        title: "Grounds required",
        message: "Grounds for appeal must be provided as required by BR-PMS-092.",
      });
      return;
    }
    appeal.mutate(grounds, {
      onSuccess: () => {
        notifications.show({
          color: "green",
          title: "Appeal submitted",
          message: "Your appeal has been submitted for director review.",
        });
        setGrounds("");
        onClose();
      },
      onError: (err) => {
        notifications.show({
          color: "red",
          title: "Appeal submission failed",
          message: errorMessage(err),
        });
      },
    });
  };

  return (
    <Modal opened={opened} onClose={onClose} title="Submit Appeal">
      <form onSubmit={handleSubmit}>
        <Stack gap="md">
          <Text size="sm">
            File an appeal against rejection for <strong>{applicationTitle}</strong>.
          </Text>
          <Textarea
            label="Grounds for Appeal"
            description="Detail the grounds on which you are contesting this decision (BR-PMS-092..094)."
            placeholder="State your technical justification and grounds for appeal..."
            required
            minRows={4}
            value={grounds}
            onChange={(e) => setGrounds(e.currentTarget.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={onClose} disabled={appeal.isPending}>
              Cancel
            </Button>
            <Button color="blue" type="submit" loading={appeal.isPending}>
              Submit Appeal
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
