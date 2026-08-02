import { useState } from "react";
import {
  Alert, Grid, NumberInput, Select, Stack, Switch, TagsInput, Textarea,
  TextInput,
} from "@mantine/core";
import { DateTimePicker } from "@mantine/dates";
import { notifications } from "@mantine/notifications";
import { FaInfoCircle } from "react-icons/fa";

import { FormModal } from "../../../ui/components/FormModal";
import { errorMessage } from "../../../lib/http";
import { useCompanies, useCreatePosting } from "../api/hooks";

/** Creating a posting.
 *
 *  The eligibility rule is built from a few named controls rather than a raw
 *  JSON box. Two reasons: the server's rule vocabulary is a closed set and an
 *  unknown field DENIES everyone, and a free-text JSON field on a screen that
 *  decides who may apply is a footgun aimed at students.
 */
export function NewPostingModal({ opened, onClose }: {
  opened: boolean;
  onClose: () => void;
}) {
  const companies = useCompanies();
  const create = useCreatePosting();

  const [companyId, setCompanyId] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [kind, setKind] = useState<string | null>("fte");
  const [year, setYear] = useState("2026-27");
  const [description, setDescription] = useState("");
  const [location, setLocation] = useState("");
  const [ctc, setCtc] = useState<number | string>("");
  const [seats, setSeats] = useState<number | string>("");
  const [closesAt, setClosesAt] = useState<Date | null>(null);
  const [isDreamSlot, setIsDreamSlot] = useState(false);
  const [dreamNote, setDreamNote] = useState("");

  const [minCpi, setMinCpi] = useState<number | string>("");
  const [disciplines, setDisciplines] = useState<string[]>([]);
  const [maxBacklogs, setMaxBacklogs] = useState<number | string>("");
  const [skills, setSkills] = useState<string[]>([]);

  // Only approved companies may hold a posting (PC-BR-006), so the picker
  // cannot offer one that would be rejected on submit.
  const options = (companies.data?.results ?? [])
    .filter((c) => c.can_operate)
    .map((c) => ({ value: String(c.id), label: c.name }));

  function buildRule(): Record<string, unknown> {
    const clauses: Record<string, unknown>[] = [];
    if (minCpi !== "") clauses.push({ gte: ["cpi", Number(minCpi)] });
    if (disciplines.length) clauses.push({ in: ["discipline", disciplines] });
    if (maxBacklogs !== "") {
      clauses.push({ lte: ["active_backlogs", Number(maxBacklogs)] });
    }
    if (skills.length) clauses.push({ has_all: ["skills", skills] });
    if (!clauses.length) return {};          // no rule = no restriction
    if (clauses.length === 1) return clauses[0]!;
    return { all: clauses };
  }

  function submit() {
    create.mutate(
      {
        company_id: companyId ? Number(companyId) : undefined,
        title, kind, placement_year: year, description, location,
        ctc_lpa: ctc === "" ? null : String(ctc),
        seats: seats === "" ? null : Number(seats),
        closes_at: closesAt ? closesAt.toISOString() : null,
        eligibility_rule: buildRule(),
        is_dream_slot: isDreamSlot,
        dream_slot_note: dreamNote,
      },
      {
        onSuccess: () => {
          notifications.show({
            color: "green", title: "Posting created",
            message: "Saved as a draft. Publish it when the details are final.",
          });
          onClose();
        },
        onError: (e) => notifications.show({
          color: "red", title: "Could not create posting",
          message: errorMessage(e),
        }),
      },
    );
  }

  return (
    <FormModal
      opened={opened} onClose={onClose}
      title="New job posting"
      subtitle="Saved as a draft — nothing is visible to students until published"
      onSubmit={submit} submitLabel="Create draft"
      submitting={create.isPending} error={create.error}
      disabled={!title.trim() || !companyId}
    >
      <Stack gap="md">
        <Grid>
          <Grid.Col span={{ base: 12, sm: 6 }}>
            <Select
              label="Company" required data={options} value={companyId}
              onChange={setCompanyId} searchable
              placeholder={options.length ? "Select" : "No approved companies"}
              description="Only approved companies can be selected"
            />
          </Grid.Col>
          <Grid.Col span={{ base: 12, sm: 6 }}>
            <TextInput
              label="Role title" required value={title}
              onChange={(e) => setTitle(e.currentTarget.value)}
              placeholder="Backend Engineer"
            />
          </Grid.Col>
          <Grid.Col span={{ base: 12, sm: 4 }}>
            <Select
              label="Type" data={[
                { value: "fte", label: "Full time" },
                { value: "internship", label: "Internship" },
                { value: "ppo", label: "Pre-placement offer" },
              ]} value={kind} onChange={setKind}
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
          <Grid.Col span={{ base: 12, sm: 4 }}>
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

        <Switch
          label="Declare this a Dream Slot"
          description="Policy rule 7 — placed students may also appear, and the
                       switch rules do not close their application."
          checked={isDreamSlot}
          onChange={(e) => setIsDreamSlot(e.currentTarget.checked)}
        />
        {isDreamSlot && (
          <TextInput
            label="Dream Slot note" value={dreamNote}
            onChange={(e) => setDreamNote(e.currentTarget.value)}
            placeholder="Which students the Placement Cell has declared eligible"
          />
        )}

        <Alert variant="light" color="blue" icon={<FaInfoCircle />}>
          Eligibility criteria are frozen when the posting is published, so they
          cannot change under students who have already applied. Leave a field
          blank to place no restriction on it.
        </Alert>

        <Grid>
          <Grid.Col span={{ base: 12, sm: 6 }}>
            <NumberInput
              label="Minimum CPI" value={minCpi} onChange={setMinCpi}
              decimalScale={2} min={0} max={10}
              description="Checked against the last declared result"
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
              placeholder="Matched against the student's profile"
            />
          </Grid.Col>
        </Grid>
      </Stack>
    </FormModal>
  );
}
