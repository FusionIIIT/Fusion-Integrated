import React, { useState } from "react";
import { Alert, Button, Group, Modal, NumberInput, Stack, TextInput, Textarea } from "@mantine/core";
import { getApiErrorMessage, useCreateSection } from "../api/hooks";

export interface CreateSectionModalProps {
  opened: boolean;
  onClose: () => void;
  courseId: number;
}

export const CreateSectionModal: React.FC<CreateSectionModalProps> = ({
  opened,
  onClose,
  courseId,
}) => {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [order, setOrder] = useState<number | string>(0);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const createSectionMutation = useCreateSection();

  const handleClose = () => {
    setErrorMsg(null);
    setTitle("");
    setDescription("");
    setOrder(0);
    onClose();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    try {
      await createSectionMutation.mutateAsync({
        course: courseId,
        title,
        description: description || undefined,
        order: typeof order === "number" ? order : parseInt(order) || 0,
        is_published: true,
      });
      handleClose();
    } catch (err: unknown) {
      setErrorMsg(getApiErrorMessage(err));
    }
  };

  return (
    <Modal opened={opened} onClose={handleClose} title="Add New Module Section" size="md">
      <form onSubmit={handleSubmit}>
        <Stack gap="md">
          {errorMsg && (
            <Alert color="red" title="Error" withCloseButton onClose={() => setErrorMsg(null)}>
              {errorMsg}
            </Alert>
          )}

          <TextInput
            label="Section Title"
            placeholder="e.g. Week 1: Introduction to Data Structures"
            value={title}
            onChange={(e) => setTitle(e.currentTarget.value)}
            required
          />

          <Textarea
            label="Description"
            placeholder="Overview of this module's topics..."
            value={description}
            onChange={(e) => setDescription(e.currentTarget.value)}
          />

          <NumberInput
            label="Sort Order"
            value={order}
            onChange={(val) => setOrder(val)}
            min={0}
          />

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={handleClose}>
              Cancel
            </Button>
            <Button type="submit" loading={createSectionMutation.isPending}>
              Create Section
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
};

export default CreateSectionModal;
