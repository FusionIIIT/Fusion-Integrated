import { useState } from "react";
import {
  Alert, Badge, Button, Card, Container, Grid, NumberInput, Select, Stack,
  TagsInput, Text, Textarea, TextInput,
} from "@mantine/core";
import { DateTimePicker } from "@mantine/dates";
import { notifications } from "@mantine/notifications";
import { FaClipboardList, FaInfoCircle, FaPlus } from "react-icons/fa";

import { errorMessage } from "../../lib/http";
import { DataTable } from "../../ui/components/DataTable";
import { ErrorState } from "../../ui/components/ErrorState";
import { FormModal } from "../../ui/components/FormModal";
import { PageHeader } from "../../ui/components/PageHeader";
import { StatusBadge } from "../../ui/components/StatusBadge";
import { useRecruiterAuth } from "../RecruiterAuth";
import {
  useCreateMyPosting, useMyPostings, usePublishMyPosting, type Posting,
} from "../api";

export default function RecruiterPostingsPage() {
  const { session } = useRecruiterAuth();
  const { data, isPending, error } = useMyPostings();
  const publish = usePublishMyPosting();
  const [creating, setCreating] = useState(false);

  const approved = session?.company.approval_status === "approved";

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  return (
    <Container size="xl">
      <PageHeader
        title="My Postings"
        subtitle={`Roles ${session?.company.name ?? "your company"} has opened`}
        action={
          <Button
            leftSection={<FaPlus size={12} />} disabled={!approved}
            onClick={() => setCreating(true)}
          >
            New posting
          </Button>
        }
      />

      <Card padding="lg">
        <DataTable<Posting>
          rows={data?.results ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={900}
          columns={[
            {
              key: "title", header: "Role",
              render: (r) => (
                <Stack gap={0}>
                  <Text fw={600}>{r.title}</Text>
                  <Text size="xs" c="dimmed">{r.location || "—"}</Text>
                </Stack>
              ),
            },
            {
              key: "kind", header: "Type",
              render: (r) => (
                <Badge variant="default" size="sm">
                  {r.kind === "fte" ? "Full time"
                    : r.kind === "ppo" ? "PPO" : "Internship"}
                </Badge>
              ),
            },
            { key: "ctc_lpa", header: "CTC (LPA)", align: "right",
              render: (r) => r.ctc_lpa ?? "—" },
            { key: "seats", header: "Seats", align: "right",
              render: (r) => r.seats?.toString() ?? "—" },
            { key: "closes_at", header: "Applications close",
              render: (r) => r.closes_at
                ? new Date(r.closes_at).toLocaleDateString() : "—" },
            { key: "status", header: "Status",
              render: (r) => <StatusBadge status={r.status} /> },
            {
              key: "actions", header: "", align: "right",
              render: (r) => r.status === "draft" ? (
                <Button
                  size="xs" variant="light" loading={publish.isPending}
                  onClick={() => publish.mutate(r.id, {
                    onSuccess: () => notifications.show({
                      color: "green", title: "Published",
                      message: "Students can now see and apply to this role.",
                    }),
                    onError: (e) => notifications.show({
                      color: "red", title: "Could not publish",
                      message: errorMessage(e),
                    }),
                  })}
                >
                  Publish
                </Button>
              ) : <Text size="xs" c="dimmed">—</Text>,
            },
          ]}
          empty={{
            icon: FaClipboardList,
            title: "You have not posted any roles yet",
            description: approved
              ? "Create a draft, then publish it when the details are final."
              : "Posting is available once the placement office approves you.",
          }}
        />
      </Card>

      <NewPostingModal opened={creating} onClose={() => setCreating(false)} />
    </Container>
  );
}

function NewPostingModal({ opened, onClose }: {
  opened: boolean; onClose: () => void;
}) {
  const create = useCreateMyPosting();
  const [title, setTitle] = useState("");
  const [kind, setKind] = useState<string | null>("fte");
  const [year, setYear] = useState("2026-27");
  const [description, setDescription] = useState("");
  const [location, setLocation] = useState("");
  const [ctc, setCtc] = useState<number | string>("");
  const [seats, setSeats] = useState<number | string>("");
  const [closesAt, setClosesAt] = useState<Date | null>(null);
  const [minCpi, setMinCpi] = useState<number | string>("");
  const [disciplines, setDisciplines] = useState<string[]>([]);
  const [maxBacklogs, setMaxBacklogs] = useState<number | string>("");
  const [skills, setSkills] = useState<string[]>([]);

  function buildRule(): Record<string, unknown> {
    const clauses: Record<string, unknown>[] = [];
    if (minCpi !== "") clauses.push({ gte: ["cpi", Number(minCpi)] });
    if (disciplines.length) clauses.push({ in: ["discipline", disciplines] });
    if (maxBacklogs !== "") {
      clauses.push({ lte: ["active_backlogs", Number(maxBacklogs)] });
    }
    if (skills.length) clauses.push({ has_all: ["skills", skills] });
    if (!clauses.length) return {};
    if (clauses.length === 1) return clauses[0]!;
    return { all: clauses };
  }

  return (
    <FormModal
      opened={opened} onClose={onClose}
      title="Post a role"
      subtitle="Saved as a draft — students see nothing until you publish"
      onSubmit={() => create.mutate(
        {
          // No company_id: the server takes it from the credential.
          title, kind, placement_year: year, description, location,
          ctc_lpa: ctc === "" ? null : String(ctc),
          seats: seats === "" ? null : Number(seats),
          closes_at: closesAt ? closesAt.toISOString() : null,
          eligibility_rule: buildRule(),
        },
        {
          onSuccess: () => {
            notifications.show({
              color: "green", title: "Draft created",
              message: "Publish it when you are ready.",
            });
            onClose();
          },
          onError: (e) => notifications.show({
            color: "red", title: "Could not create", message: errorMessage(e),
          }),
        },
      )}
      submitLabel="Create draft" submitting={create.isPending}
      error={create.error} disabled={!title.trim()}
    >
      <Stack gap="md">
        <Grid>
          <Grid.Col span={{ base: 12, sm: 8 }}>
            <TextInput
              label="Role title" required value={title}
              onChange={(e) => setTitle(e.currentTarget.value)}
            />
          </Grid.Col>
          <Grid.Col span={{ base: 12, sm: 4 }}>
            <Select
              label="Type" value={kind} onChange={setKind}
              data={[
                { value: "fte", label: "Full time" },
                { value: "internship", label: "Internship" },
                { value: "ppo", label: "Pre-placement offer" },
              ]}
            />
          </Grid.Col>
          <Grid.Col span={{ base: 12, sm: 4 }}>
            <TextInput
              label="Placement year" required value={year}
              onChange={(e) => setYear(e.currentTarget.value)}
            />
          </Grid.Col>
          <Grid.Col span={{ base: 12, sm: 4 }}>
            <TextInput
              label="Location" value={location}
              onChange={(e) => setLocation(e.currentTarget.value)}
            />
          </Grid.Col>
          <Grid.Col span={{ base: 12, sm: 4 }}>
            <NumberInput
              label="CTC (LPA)" value={ctc} onChange={setCtc}
              decimalScale={2} min={0}
            />
          </Grid.Col>
          <Grid.Col span={{ base: 12, sm: 4 }}>
            <NumberInput label="Seats" value={seats} onChange={setSeats} min={0} />
          </Grid.Col>
          <Grid.Col span={{ base: 12, sm: 8 }}>
            <DateTimePicker
              label="Applications close" value={closesAt} onChange={setClosesAt}
              description="Required before publishing"
            />
          </Grid.Col>
        </Grid>

        <Textarea
          label="Role description" autosize minRows={4} value={description}
          onChange={(e) => setDescription(e.currentTarget.value)}
          description="Required before publishing"
        />

        <Alert variant="light" color="blue" icon={<FaInfoCircle />}>
          <Text size="sm">
            Eligibility criteria are locked when you publish, so they cannot
            change under students who have already applied. Leave a field blank
            to place no restriction on it.
          </Text>
        </Alert>

        <Grid>
          <Grid.Col span={{ base: 12, sm: 6 }}>
            <NumberInput
              label="Minimum CPI" value={minCpi} onChange={setMinCpi}
              decimalScale={2} min={0} max={10}
              description="Checked against the institute's declared result"
            />
          </Grid.Col>
          <Grid.Col span={{ base: 12, sm: 6 }}>
            <NumberInput
              label="Maximum active backlogs" value={maxBacklogs}
              onChange={setMaxBacklogs} min={0}
            />
          </Grid.Col>
          <Grid.Col span={12}>
            <TagsInput
              label="Disciplines" value={disciplines} onChange={setDisciplines}
              placeholder="CSE, ECE — leave empty for all"
            />
          </Grid.Col>
          <Grid.Col span={12}>
            <TagsInput
              label="Required skills" value={skills} onChange={setSkills}
            />
          </Grid.Col>
        </Grid>
      </Stack>
    </FormModal>
  );
}
