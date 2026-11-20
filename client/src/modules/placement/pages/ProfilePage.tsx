import { useState } from "react";
import {
  Alert, Anchor, Badge, Button, Card, Container, Divider, Group, Select, SimpleGrid,
  Text, TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaExclamationTriangle, FaFileAlt, FaPlus, FaPrint, FaTrash } from "react-icons/fa";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { Field, FormRow, FormSection } from "../../../ui/components/FormSection";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useAttachDocument, useDeleteDocument, useMyDocuments, useMyProfile,
} from "../api/hooks";
import type { CandidateRecord, ProfileDocument } from "../api/types";

function kindLabel(kind: string) {
  return DOC_KINDS.find((k) => k.value === kind)?.label ?? kind;
}

const DOC_KINDS = [
  { value: "certificate", label: "Certificate" },
  { value: "offer_letter", label: "Offer letter" },
  { value: "other", label: "Other" },
];

function Fact({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div>
      <Text size="xs" c="dimmed" tt="uppercase">{label}</Text>
      <Text fw={600}>{value || "—"}</Text>
    </div>
  );
}

/** PC-UC-023: a structured resume built only from the saved profile data. */
function Resume({ profile }: { profile: CandidateRecord }) {
  const cpi = profile.academic?.cpi;
  return (
    <Card padding="lg" mt="md" id="structured-resume">
      <Group justify="space-between">
        <Text fw={600}>Structured resume</Text>
        <Button size="xs" variant="default" leftSection={<FaPrint size={11} />}
          onClick={() => window.print()}>
          Print
        </Button>
      </Group>
      <Divider my="sm" />
      <Text fw={700} size="lg">{profile.name}</Text>
      <Text size="sm" c="dimmed">{[profile.roll_no, profile.email].filter(Boolean).join(" · ")}</Text>
      <Text fw={600} mt="md">Education</Text>
      <Text size="sm">
        {[profile.programme, profile.discipline].filter(Boolean).join(", ") || "Programme not recorded"}
        {profile.batch_year ? `, batch of ${profile.batch_year}` : ""}
      </Text>
      <Text size="sm">
        {cpi ? `CPI ${cpi}` : "No declared result yet"}
        {profile.academic?.semester ? ` (as of semester ${profile.academic.semester})` : ""}
      </Text>
      {profile.resume_link && (
        <>
          <Text fw={600} mt="md">Full resume</Text>
          <Anchor href={profile.resume_link} target="_blank" rel="noreferrer" size="sm">
            Open the resume you keep on the Fusion portal
          </Anchor>
        </>
      )}
    </Card>
  );
}

function AddDocumentModal({ opened, onClose }: { opened: boolean; onClose: () => void }) {
  const attach = useAttachDocument();
  const [url, setUrl] = useState("");
  const [title, setTitle] = useState("");
  const [kind, setKind] = useState<string | null>("certificate");

  function submit() {
    attach.mutate({ url, kind: kind ?? "certificate", title }, {
      onSuccess: () => {
        notifications.show({ color: "green", title: "Document added", message: title || "Saved." });
        setUrl(""); setTitle("");
        onClose();
      },
    });
  }

  return (
    <FormModal
      opened={opened} onClose={onClose} title="Add a document"
      subtitle="Share the file from Google Drive and paste its link"
      onSubmit={submit} submitLabel="Add document" submitting={attach.isPending}
      error={attach.error} disabled={!url.trim()} disabledReason="Paste the Drive link."
    >
      <FormSection first title="Document">
        <FormRow>
          <Field span={12}>
            <TextInput label="Drive link" required placeholder="https://drive.google.com/…"
              value={url} onChange={(e) => setUrl(e.currentTarget.value)} />
          </Field>
          <Field span={7}>
            <TextInput label="Title" maxLength={160} value={title}
              onChange={(e) => setTitle(e.currentTarget.value)} />
          </Field>
          <Field span={5}>
            <Select label="Kind" data={DOC_KINDS} value={kind} onChange={setKind}
              allowDeselect={false} />
          </Field>
        </FormRow>
      </FormSection>
    </FormModal>
  );
}

function Documents() {
  const { data, isPending, error } = useMyDocuments();
  const remove = useDeleteDocument();
  const [adding, setAdding] = useState(false);
  const rows = data?.results ?? [];

  return (
    <Card padding="lg" mt="md">
      <Group justify="space-between" mb="sm">
        <div>
          <Text fw={600}>Placement documents</Text>
          <Text size="xs" c="dimmed">
            Certificates and offer letters, as Google Drive links shared with the placement office.
          </Text>
        </div>
        <Button size="xs" leftSection={<FaPlus size={11} />} onClick={() => setAdding(true)}>
          Add document
        </Button>
      </Group>
      {error ? <ErrorState error={error} /> : (
        <DataTable<ProfileDocument>
          rows={rows}
          loading={isPending}
          rowKey={(d) => d.id}
          minWidth={520}
          columns={[
            { key: "title", header: "Document",
              render: (d) => (
                <Anchor href={d.download_url} size="sm" target="_blank" rel="noreferrer">
                  {d.title}
                </Anchor>
              ) },
            { key: "kind", header: "Kind",
              render: (d) => <Badge size="sm" variant="default">{kindLabel(d.kind)}</Badge> },
            { key: "actions", header: "", align: "right",
              render: (d) => (
                <Button size="xs" variant="subtle" color="red"
                  leftSection={<FaTrash size={10} />}
                  loading={remove.isPending && remove.variables === d.id}
                  onClick={() => remove.mutate(d.id)} aria-label={`Remove ${d.title}`}>
                  Remove
                </Button>
              ) },
          ]}
          empty={{
            icon: FaFileAlt,
            title: "No documents yet",
            description: "Add a certificate or an offer letter as a Drive link.",
          }}
        />
      )}
      <AddDocumentModal opened={adding} onClose={() => setAdding(false)} />
    </Card>
  );
}

export default function ProfilePage() {
  const { data, isPending, error } = useMyProfile();

  if (error) return <Container size="lg"><ErrorState error={error} /></Container>;
  if (isPending || !data) {
    return <Container size="lg"><Text c="dimmed">Loading…</Text></Container>;
  }

  return (
    <Container size="lg">
      <PageHeader title="My Profile"
        subtitle="Your placement profile, from the Fusion portal and this module" />
      {!data.profile_completed && (
        <Alert color="orange" variant="light" icon={<FaExclamationTriangle />}
          title="Your profile is not complete">
          <Text size="sm">
            Complete your profile on the Fusion portal. You cannot apply until it is complete.
          </Text>
        </Alert>
      )}
      <Card padding="lg" mt="md">
        <SimpleGrid cols={{ base: 2, sm: 4 }}>
          <Fact label="Name" value={data.name} />
          <Fact label="Roll number" value={data.roll_no} />
          <Fact label="Programme" value={data.programme} />
          <Fact label="Discipline" value={data.discipline} />
          <Fact label="Batch" value={data.batch_year} />
          <Fact label="CPI" value={data.academic?.cpi} />
          <Fact label="Profile" value={data.profile_completed ? "Complete" : "Incomplete"} />
        </SimpleGrid>
      </Card>
      <Resume profile={data} />
      <Documents />
    </Container>
  );
}
