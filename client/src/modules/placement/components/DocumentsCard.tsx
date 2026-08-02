import { useState } from "react";
import {
  ActionIcon, Alert, Badge, Button, Card, Group, Select, Stack, Text, TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  FaExternalLinkAlt, FaFileAlt, FaInfoCircle, FaLink, FaTrash,
} from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import {
  documentDownloadUrl, useAttachDocument, useDeleteDocument, useMyDocuments,
} from "../api/hooks";

const KINDS = [
  { value: "resume", label: "Resume" },
  { value: "certificate", label: "Certificate" },
  { value: "other", label: "Other" },
];

/** A shape check only. The server does the validation that counts. */
function looksLikeDrive(url: string): boolean {
  return /^https:\/\/(drive|docs)\.google\.com\//.test(url.trim());
}

export function DocumentsCard() {
  const { data, isPending } = useMyDocuments();
  const attach = useAttachDocument();
  const remove = useDeleteDocument();
  const [kind, setKind] = useState<string>("resume");
  const [url, setUrl] = useState("");

  const rows = data?.results ?? [];
  const dirty = url.trim().length > 0;
  const badShape = dirty && !looksLikeDrive(url);

  function submit() {
    attach.mutate({ url: url.trim(), kind }, {
      onSuccess: () => {
        notifications.show({
          color: "green", title: "Document linked",
          message: "Recruiters reach it through the portal, not the raw link.",
        });
        setUrl("");
      },
      onError: (e) => notifications.show({
        color: "red", title: "Link refused", message: errorMessage(e),
      }),
    });
  }

  return (
    <Card padding="lg" mb="md">
      <Group justify="space-between" mb="sm">
        <div>
          <Text fw={600}>Documents</Text>
          <Text size="xs" c="dimmed">
            A resume is required before you can apply.
          </Text>
        </div>
        <Select
          data={KINDS} value={kind} onChange={(v) => setKind(v ?? "resume")}
          w={150}
        />
      </Group>

      <Alert
        variant="light" color="blue" icon={<FaInfoCircle />} mb="md"
        title="Share the file before you paste the link"
      >
        <Text size="sm">
          In Drive, open <b>Share → General access</b> and set it to{" "}
          <b>Anyone with the link — Viewer</b>. A recruiter cannot open a file
          that is still restricted to you.
        </Text>
        <Text size="sm" mt={6} c="dimmed">
          Anyone holding that link can open it, so keep the document free of
          anything you would not want a company to read.
        </Text>
      </Alert>

      <Group align="flex-start" gap="xs" mb="md" wrap="nowrap">
        <TextInput
          flex={1}
          placeholder="https://drive.google.com/file/d/…/view"
          value={url}
          onChange={(e) => setUrl(e.currentTarget.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && dirty && !badShape) submit();
          }}
          error={badShape ? "That is not a Google Drive link." : undefined}
          leftSection={<FaLink size={12} />}
        />
        <Button
          onClick={submit} loading={attach.isPending}
          disabled={!dirty || badShape}
        >
          Attach
        </Button>
      </Group>

      {isPending && <Text size="sm" c="dimmed">Loading…</Text>}

      {!isPending && rows.length === 0 && (
        <Text size="sm" c="dimmed">
          Nothing linked yet. Start with your resume.
        </Text>
      )}

      <Stack gap="xs">
        {rows.map((doc) => (
          <Group key={doc.id} justify="space-between" wrap="nowrap">
            <Group gap="sm" wrap="nowrap" style={{ minWidth: 0 }}>
              <FaFileAlt color="var(--mantine-color-blue-6)" />
              <Stack gap={0} style={{ minWidth: 0 }}>
                <Text size="sm" fw={500} lineClamp={1}>
                  {doc.title || doc.original_filename || "Document"}
                </Text>
                <Text size="xs" c="dimmed">
                  {new Date(doc.created_at).toLocaleDateString()}
                </Text>
              </Stack>
              <Badge variant="light" size="sm">{doc.kind}</Badge>
            </Group>
            <Group gap={4} wrap="nowrap">
              {/* The authorising view, never Drive directly. */}
              <ActionIcon
                component="a" href={documentDownloadUrl(doc.id)}
                target="_blank" rel="noopener noreferrer"
                variant="subtle" color="gray" aria-label="Open"
              >
                <FaExternalLinkAlt size={12} />
              </ActionIcon>
              <ActionIcon
                variant="subtle" color="red" aria-label="Remove"
                loading={remove.isPending}
                onClick={() => remove.mutate(doc.id, {
                  onError: (e) => notifications.show({
                    color: "red", title: "Could not remove",
                    message: errorMessage(e),
                  }),
                })}
              >
                <FaTrash size={12} />
              </ActionIcon>
            </Group>
          </Group>
        ))}
      </Stack>
    </Card>
  );
}
