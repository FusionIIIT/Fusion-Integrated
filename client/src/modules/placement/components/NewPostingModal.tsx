import { useMemo, useState } from "react";
import {
  Alert, NumberInput, Select, Stack, Switch, TagsInput, Textarea, TextInput,
} from "@mantine/core";
import { DateTimePicker } from "@mantine/dates";
import { notifications } from "@mantine/notifications";
import { FaInfoCircle } from "react-icons/fa";

import { FormModal } from "../../../ui/components/FormModal";
import { Field, FormRow, FormSection } from "../../../ui/components/FormSection";
import { errorMessage } from "../../../lib/http";
import { useCompanies, useCreatePosting, useSeasons } from "../api/hooks";

const KINDS = [
  { value: "fte", label: "Full time" },
  { value: "internship", label: "Internship" },
  { value: "ppo", label: "Pre-placement offer" },
];

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
  const seasons = useSeasons();
  const create = useCreatePosting();

  const [companyId, setCompanyId] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [kind, setKind] = useState<string | null>("fte");
  const [year, setYear] = useState<string | null>(null);
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
  const companyOptions = useMemo(
    () => (companies.data?.results ?? [])
      .filter((c) => c.can_operate)
      .map((c) => ({ value: String(c.id), label: c.name })),
    [companies.data],
  );

  const seasonOptions = useMemo(
    () => (seasons.data ?? []).map((s) => ({
      value: s.season,
      label: s.is_active ? `${s.season} (active)` : s.season,
    })),
    [seasons.data],
  );

  // Falls back to the active season once it loads, without clobbering a choice.
  const activeSeason = seasons.data?.find((s) => s.is_active)?.season ?? null;
  const season = year ?? activeSeason;

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

  // Stated in the footer, so a greyed-out button is never a guessing game.
  const blocker =
    !companyId ? "Choose a company to continue."
      : !title.trim() ? "A role title is required."
        : !season ? "Choose a placement season."
          : undefined;

  function submit() {
    create.mutate(
      {
        company_id: companyId ? Number(companyId) : undefined,
        title, kind, placement_year: season ?? "", description, location,
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
      opened={opened} onClose={onClose} size="xl"
      title="New job posting"
      subtitle="Saved as a draft — nothing is visible to students until published"
      onSubmit={submit} submitLabel="Create draft"
      submitting={create.isPending} error={create.error}
      disabled={Boolean(blocker)} disabledReason={blocker}
    >
      <Stack gap="xl">
        <FormSection first title="Role">
          <FormRow>
            <Field span={7}>
              <Select
                label="Company" withAsterisk
                data={companyOptions} value={companyId} onChange={setCompanyId}
                searchable nothingFoundMessage="No match"
                placeholder={companyOptions.length
                  ? "Search companies" : "No approved companies yet"}
                disabled={!companyOptions.length}
                description="Only approved companies can be selected"
              />
            </Field>
            <Field span={5}>
              <Select
                label="Engagement" data={KINDS} value={kind} onChange={setKind}
                allowDeselect={false}
              />
            </Field>
            <Field span={7}>
              <TextInput
                label="Role title" withAsterisk value={title}
                onChange={(e) => setTitle(e.currentTarget.value)}
                placeholder="Backend Engineer"
              />
            </Field>
            <Field span={5}>
              <TextInput
                label="Location" value={location}
                onChange={(e) => setLocation(e.currentTarget.value)}
                placeholder="Bengaluru / Remote"
              />
            </Field>
          </FormRow>
        </FormSection>

        <FormSection
          title="Offer and timeline"
          hint="A description and a closing date are both required before this posting can be published."
        >
          <FormRow>
            <Field span={4}>
              <Select
                label="Season" withAsterisk
                data={seasonOptions} value={season} onChange={setYear}
                allowDeselect={false}
                placeholder={seasons.isPending ? "Loading…" : "Select a season"}
                disabled={!seasonOptions.length}
                description={seasonOptions.length
                  ? undefined : "No placement policy is configured yet"}
              />
            </Field>
            <Field span={4}>
              <NumberInput
                label="CTC" value={ctc} onChange={setCtc}
                decimalScale={2} min={0} suffix=" LPA"
                hideControls placeholder="0.00"
              />
            </Field>
            <Field span={4}>
              <NumberInput
                label="Seats" value={seats} onChange={setSeats} min={0}
                hideControls placeholder="Unlimited"
              />
            </Field>
            <Field span={12}>
              <DateTimePicker
                label="Applications close" value={closesAt}
                onChange={setClosesAt} clearable minDate={new Date()}
                placeholder="Select a date and time"
                description="Required before publishing"
              />
            </Field>
          </FormRow>
        </FormSection>

        <FormSection
          title="Role description"
          hint="Shown to students on the posting. Required before publishing."
        >
          <Textarea
            aria-label="Role description"
            autosize minRows={5} maxRows={12} value={description}
            onChange={(e) => setDescription(e.currentTarget.value)}
            placeholder="Responsibilities, tech stack, selection process…"
          />
        </FormSection>

        <FormSection
          title="Eligibility"
          hint="Leave a field blank to place no restriction on it."
        >
          <Stack gap="md">
            <Alert variant="light" color="blue" icon={<FaInfoCircle />} p="sm">
              Criteria are frozen when the posting is published, so they cannot
              change under students who have already applied.
            </Alert>
            <FormRow>
              <Field span={6}>
                <NumberInput
                  label="Minimum CPI" value={minCpi} onChange={setMinCpi}
                  decimalScale={2} min={0} max={10} step={0.1}
                  hideControls placeholder="No minimum"
                  description="Checked against the last declared result"
                />
              </Field>
              <Field span={6}>
                <NumberInput
                  label="Maximum active backlogs" value={maxBacklogs}
                  onChange={setMaxBacklogs} min={0}
                  hideControls placeholder="No limit"
                />
              </Field>
              <Field span={12}>
                <TagsInput
                  label="Disciplines" value={disciplines}
                  onChange={setDisciplines}
                  placeholder="Type a code and press Enter — empty means all"
                />
              </Field>
              <Field span={12}>
                <TagsInput
                  label="Required skills" value={skills} onChange={setSkills}
                  placeholder="Matched against the student's profile"
                />
              </Field>
            </FormRow>
          </Stack>
        </FormSection>

        <FormSection title="Dream Slot">
          <Stack gap="sm">
            <Switch
              label="Declare this a Dream Slot"
              description="Policy rule 7 — placed students may also appear, and the switch rules do not close their application."
              checked={isDreamSlot}
              onChange={(e) => setIsDreamSlot(e.currentTarget.checked)}
            />
            <TextInput
              label="Dream Slot note" value={dreamNote}
              onChange={(e) => setDreamNote(e.currentTarget.value)}
              placeholder="Which students the Placement Cell has declared eligible"
              disabled={!isDreamSlot}
            />
          </Stack>
        </FormSection>
      </Stack>
    </FormModal>
  );
}
