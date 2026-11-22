import { useState } from "react";
import { Button, Card, Checkbox, Container, NumberInput, Stack, Textarea, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useNavigate } from "react-router-dom";

import { PageHeader } from "../../../ui/components/PageHeader";
import { useCreateFile } from "../api/hooks";

export default function CreateFilePage() {
  const navigate = useNavigate();
  const createMutation = useCreateFile();

  const [subject, setSubject] = useState("");
  const [initialComment, setInitialComment] = useState("");
  const [isDraft, setIsDraft] = useState(false);
  const [recipientUserId, setRecipientUserId] = useState<number | string>("");
  const [recipientDesignation, setRecipientDesignation] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!subject.trim()) {
      notifications.show({ color: "red", message: "Subject is required." });
      return;
    }
    if (!initialComment.trim()) {
      notifications.show({ color: "red", message: "Initial comment is required." });
      return;
    }
    if (!isDraft && !recipientUserId) {
      notifications.show({
        color: "red",
        message: "Recipient user ID is required when not saving as draft.",
      });
      return;
    }

    createMutation.mutate(
      {
        subject,
        initial_comment: initialComment,
        is_draft: isDraft,
        recipient_user_id: isDraft ? null : Number(recipientUserId),
        recipient_designation: recipientDesignation,
      },
      {
        onSuccess: (data) => {
          notifications.show({
            color: "green",
            message: `File ${data.file_number} created successfully.`,
          });
          navigate(isDraft ? "/filetracking/inbox" : "/filetracking/outbox");
        },
        onError: (err: any) => {
          notifications.show({
            color: "red",
            message: err?.response?.data?.error?.message || "Failed to create file.",
          });
        },
      }
    );
  };

  return (
    <Container size="sm" py="md">
      <PageHeader
        title="Create New File"
        subtitle="Initiate an institutional file as a draft or submit directly into circulation."
      />

      <Card withBorder radius="md" p="md">
        <form onSubmit={handleSubmit}>
          <Stack gap="md">
            <TextInput
              label="File Subject"
              placeholder="e.g. Purchase of Laboratory Equipment"
              required
              value={subject}
              onChange={(e) => setSubject(e.currentTarget.value)}
            />

            <Textarea
              label="Initial Note / Description"
              placeholder="Enter comprehensive initial note/remark..."
              required
              minRows={4}
              value={initialComment}
              onChange={(e) => setInitialComment(e.currentTarget.value)}
            />

            <Checkbox
              label="Save as draft (will not be circulated yet)"
              checked={isDraft}
              onChange={(e) => setIsDraft(e.currentTarget.checked)}
            />

            {!isDraft && (
              <>
                <NumberInput
                  label="Recipient Employee ID"
                  placeholder="e.g. 2"
                  required
                  value={recipientUserId}
                  onChange={(val) => setRecipientUserId(val)}
                />
                <TextInput
                  label="Recipient Designation"
                  placeholder="e.g. Dean Academic"
                  value={recipientDesignation}
                  onChange={(e) => setRecipientDesignation(e.currentTarget.value)}
                />
              </>
            )}

            <Button type="submit" loading={createMutation.isPending}>
              {isDraft ? "Save Draft" : "Circulate File"}
            </Button>
          </Stack>
        </form>
      </Card>
    </Container>
  );
}
