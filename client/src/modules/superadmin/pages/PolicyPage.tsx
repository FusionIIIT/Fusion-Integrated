import { useState } from "react";
import {
  Badge, Button, Card, Container, Group, Loader, Modal, Select, Stack, Text, Textarea,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { TbEdit, TbSettings } from "react-icons/tb";

import { errorMessage } from "../../../lib/http";
import { DataTable, type Column } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { usePolicyParams, useSupersedePolicyParam } from "../api/hooks";
import type { PolicyParameter } from "../api/types";

const PERMITTED_KEYS = [
  "archival.reversibility_window_days",
  "purge.approval_ttl_hours",
  "bulk.max_batch_size",
  "security.session_inactivity_timeout_mins",
  "security.failed_login_alert_threshold",
];

const COLUMNS: Column<PolicyParameter>[] = [
  { key: "key", header: "Parameter Key" },
  { key: "value", header: "Value" },
  { key: "value_type", header: "Type" },
  {
    key: "version",
    header: "Version",
    render: (r) => <Badge variant="outline">v{r.version}</Badge>,
  },
  {
    key: "effective_from",
    header: "Effective From",
    render: (r) => new Date(r.effective_from).toLocaleDateString(),
  },
  {
    key: "effective_to",
    header: "Effective To",
    render: (r) => r.effective_to ? new Date(r.effective_to).toLocaleDateString() : "Current",
  },
  { key: "description", header: "Description" },
];

export default function PolicyPage() {
  const { data, isPending, error } = usePolicyParams();
  const supersede = useSupersedePolicyParam();
  const [editing, setEditing] = useState<PolicyParameter | null>(null);
  const [adding, setAdding] = useState(false);
  const [key, setKey] = useState("");
  const [value, setValue] = useState("");
  const [description, setDescription] = useState("");

  if (isPending) return <Container size="xl"><Loader mt="xl" /></Container>;
  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  function openEdit(row: PolicyParameter) {
    setEditing(row);
    setKey(row.key);
    setValue(row.value);
    setDescription(row.description);
  }

  function handleSubmit() {
    supersede.mutate(
      { key, value, description },
      {
        onSuccess: () => {
          notifications.show({ color: "green", title: "Policy updated", message: `${key} updated.` });
          setEditing(null);
          setAdding(false);
          setKey("");
          setValue("");
          setDescription("");
        },
        onError: (e) =>
          notifications.show({ color: "red", title: "Update failed", message: errorMessage(e) }),
      },
    );
  }

  const isOpen = editing !== null || adding;

  return (
    <Container size="xl">
      <PageHeader
        title="System Policies"
        subtitle="Effective-dated governance parameters (append-only, never edited in place)"
        action={
          <Button leftSection={<TbEdit size={12} />} onClick={() => setAdding(true)}>
            Supersede Parameter
          </Button>
        }
      />

      <Card padding="lg" withBorder>
        <DataTable<PolicyParameter>
          rows={Array.isArray(data) ? data : (data?.results ?? [])}
          loading={isPending}
          columns={[
            ...COLUMNS,
            {
              key: "actions",
              header: "",
              render: (r) =>
                !r.effective_to ? (
                  <Button
                    size="xs"
                    variant="light"
                    leftSection={<TbEdit size={11} />}
                    onClick={() => openEdit(r)}
                  >
                    Supersede
                  </Button>
                ) : null,
            },
          ]}
          rowKey={(r) => r.id}
          empty={{
            icon: TbSettings,
            title: "No policy parameters seeded",
            description: "Run seed_superadmin_policy to initialize system governance parameters.",
          }}
        />
      </Card>

      {/* Supersede modal — inline per ADR-0010 */}
      <Modal
        opened={isOpen}
        onClose={() => { setEditing(null); setAdding(false); }}
        title={editing ? `Supersede: ${editing.key}` : "Supersede Policy Parameter"}
        transitionProps={{ duration: 0 }}
      >
        <Stack>
          {!editing && (
            <Select
              label="Parameter key"
              data={PERMITTED_KEYS}
              value={key}
              onChange={(v) => setKey(v ?? "")}
              required
            />
          )}
          {editing && <Text size="sm" c="dimmed">{editing.key} (current v{editing.version})</Text>}
          <TextInput
            label="New value"
            placeholder="e.g. 45"
            value={value}
            onChange={(e) => setValue(e.currentTarget.value)}
            required
          />
          <Textarea
            label="Reason for change"
            placeholder="Institute governance decision..."
            value={description}
            onChange={(e) => setDescription(e.currentTarget.value)}
            minRows={2}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => { setEditing(null); setAdding(false); }}>
              Cancel
            </Button>
            <Button
              loading={supersede.isPending}
              disabled={!key.trim() || !value.trim()}
              onClick={handleSubmit}
            >
              Supersede
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
