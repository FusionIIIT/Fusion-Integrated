import { useState } from "react";
import { Stack, Text, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { FormModal } from "../../../ui/components/FormModal";
import { useUpdateSystemParameter } from "../api/hooks";

export function EditParametersModal({
  paramKey,
  currentValue,
  opened,
  onClose,
}: {
  paramKey: string;
  currentValue: string;
  opened: boolean;
  onClose: () => void;
}) {
  const updateParam = useUpdateSystemParameter();
  const [value, setValue] = useState(currentValue);

  const handleSubmit = () => {
    updateParam.mutate(
      { key: paramKey, value },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Parameter Updated",
            message: `Updated ${paramKey} to "${value}".`,
          });
          onClose();
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Update Failed",
            message: errorMessage(err),
          });
        },
      },
    );
  };

  return (
    <FormModal
      opened={opened}
      onClose={onClose}
      title="Edit System Parameter"
      subtitle={`Configure runtime parameter: ${paramKey}`}
      onSubmit={handleSubmit}
      submitting={updateParam.isPending}
      submitLabel="Save Parameter"
      size="sm"
    >
      <Stack gap="md">
        <Text size="sm">
          Parameter Key: <code>{paramKey}</code>
        </Text>
        <TextInput
          label="Parameter Value"
          value={value}
          onChange={(e) => setValue(e.currentTarget.value)}
          required
        />
      </Stack>
    </FormModal>
  );
}
