import { useState } from "react";
import { Button, Group, Modal, Stack, Text, Textarea } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { useWithdrawApplication } from "../api/hooks";

export function WithdrawModal({
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
  const [reason, setReason] = useState("");
  const withdraw = useWithdrawApplication(applicationId);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!reason.trim()) {
      notifications.show({
        color: "red",
        title: "Reason required",
        message: "A withdrawal reason must be stated as required by BR-PMS-067.",
      });
      return;
    }
    withdraw.mutate(reason, {
      onSuccess: () => {
        notifications.show({
          color: "green",
          title: "Application withdrawn",
          message: "The application has been withdrawn.",
        });
        setReason("");
        onClose();
      },
      onError: (err) => {
        notifications.show({
          color: "red",
          title: "Withdrawal failed",
          message: errorMessage(err),
        });
      },
    });
  };

  return (
    <Modal opened={opened} onClose={onClose} title="Withdraw Application">
      <form onSubmit={handleSubmit}>
        <Stack gap="md">
          <Text size="sm">
            Are you sure you want to withdraw <strong>{applicationTitle}</strong>? Pre-filing withdrawal is final.
          </Text>
          <Textarea
            label="Withdrawal Reason"
            description="Mandatory per BR-PMS-067"
            placeholder="Explain why this application is being withdrawn..."
            required
            minRows={3}
            value={reason}
            onChange={(e) => setReason(e.currentTarget.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={onClose} disabled={withdraw.isPending}>
              Cancel
            </Button>
            <Button color="red" type="submit" loading={withdraw.isPending}>
              Confirm Withdrawal
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
