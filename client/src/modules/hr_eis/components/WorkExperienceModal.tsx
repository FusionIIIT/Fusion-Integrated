import { useState } from "react";
import {
  Button,
  Checkbox,
  Group,
  Modal,
  Stack,
  TextInput,
  Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useCreateWorkExperience } from "../api/hooks";

interface WorkExperienceModalProps {
  opened: boolean;
  onClose: () => void;
}

export function WorkExperienceModal({ opened, onClose }: WorkExperienceModalProps) {
  const [organization, setOrganization] = useState("");
  const [position, setPosition] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [isOngoing, setIsOngoing] = useState(false);
  const [description, setDescription] = useState("");

  const createMutation = useCreateWorkExperience();

  const resetForm = () => {
    setOrganization("");
    setPosition("");
    setStartDate("");
    setEndDate("");
    setIsOngoing(false);
    setDescription("");
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!organization.trim() || !position.trim() || !startDate) {
      notifications.show({
        title: "Required Fields",
        message: "Please fill in organization, position, and start date.",
        color: "yellow",
      });
      return;
    }

    if (!isOngoing && endDate && endDate < startDate) {
      notifications.show({
        title: "Invalid Dates",
        message: "End date cannot be earlier than start date.",
        color: "red",
      });
      return;
    }

    createMutation.mutate(
      {
        organization: organization.trim(),
        position: position.trim(),
        start_date: startDate,
        end_date: isOngoing ? null : endDate || null,
        description: description.trim(),
      },
      {
        onSuccess: () => {
          notifications.show({
            title: "Experience Added",
            message: "Work experience recorded successfully.",
            color: "green",
          });
          resetForm();
          onClose();
        },
        onError: (err) => {
          notifications.show({
            title: "Submission Error",
            message: err.message || "Failed to record work experience.",
            color: "red",
          });
        },
      }
    );
  };

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title="Add Professional Work Experience"
      size="lg"
      radius="md"
    >
      <form onSubmit={handleSubmit}>
        <Stack gap="md">
          <TextInput
            label="Organization / Institute"
            placeholder="e.g. Indian Institute of Technology Bombay"
            required
            value={organization}
            onChange={(e) => setOrganization(e.currentTarget.value)}
          />

          <TextInput
            label="Designation / Position"
            placeholder="e.g. Assistant Professor, Postdoctoral Researcher"
            required
            value={position}
            onChange={(e) => setPosition(e.currentTarget.value)}
          />

          <Group grow align="flex-start">
            <TextInput
              label="Start Date"
              type="date"
              required
              value={startDate}
              onChange={(e) => setStartDate(e.currentTarget.value)}
            />

            <TextInput
              label="End Date"
              type="date"
              disabled={isOngoing}
              value={endDate}
              onChange={(e) => setEndDate(e.currentTarget.value)}
            />
          </Group>

          <Checkbox
            label="This is my current ongoing role"
            checked={isOngoing}
            onChange={(e) => {
              setIsOngoing(e.currentTarget.checked);
              if (e.currentTarget.checked) setEndDate("");
            }}
          />

          <Textarea
            label="Key Responsibilities / Description"
            placeholder="Brief overview of research, teaching, or administrative achievements..."
            minRows={3}
            value={description}
            onChange={(e) => setDescription(e.currentTarget.value)}
          />

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" loading={createMutation.isPending}>
              Save Experience
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
