import { useState } from "react";
import {
  Alert, Button, Checkbox, Container, Group, NumberInput, Select, Stack,
  Switch, Text, TextInput, Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaInfoCircle } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormSection } from "../../../ui/components/FormSection";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useAdminConfig, useCreateDraft, useSubmitRequest,
} from "../api/hooks";
import {
  CATEGORY_LABELS, CONTINUOUS_CATEGORIES, HALF_DAY_CATEGORIES,
  LEAVE_CATEGORIES, VACATION_ONLY, type LeaveCategory,
} from "../api/types";

/** Two steps on one page: apply, then submit.
 *
 *  A draft notifies nobody, so this lets an applicant see the type and dates
 *  settled before anything reaches a Unit Head. The second step is deliberately
 *  separate — submitting is the act that starts the clock on somebody else's
 *  day. */
export default function ApplyPage() {
  const config = useAdminConfig();
  const create = useCreateDraft();
  const submit = useSubmitRequest();

  const [category, setCategory] = useState<LeaveCategory>("CASUAL");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [purpose, setPurpose] = useState("");
  const [halfDay, setHalfDay] = useState(false);
  const [half, setHalf] = useState<string | null>("morning");
  const [station, setStation] = useState(false);
  const [stationDetails, setStationDetails] = useState("");
  const [evidence, setEvidence] = useState("");
  const [draftId, setDraftId] = useState<number | null>(null);

  const kinds = config.data?.policy.category_kinds ?? {};
  const allowed = kinds[category] ?? ["faculty", "staff"];
  const halfDayAllowed = HALF_DAY_CATEGORIES.includes(category);
  const continuous = CONTINUOUS_CATEGORIES.includes(category);
  const vacationOnly = VACATION_ONLY.includes(category);
  const establishment = config.data?.policy.establishment_step_enabled ?? false;

  const ready = !!start && !!end && purpose.trim().length > 0
    && (!halfDayAllowed || !halfDay || !!half)
    && (!station || stationDetails.trim().length > 0);

  function makeDraft() {
    create.mutate({
      category,
      start_date: start,
      end_date: end,
      purpose: purpose.trim(),
      half_day: halfDayAllowed && halfDay,
      half: halfDayAllowed && halfDay ? (half ?? "") : "",
      station_leave_required: station,
      station_leave_details: station.trim(),
      medical_evidence_reference: evidence.trim(),
    }, {
      onSuccess: (row) => {
        setDraftId(row.id);
        notifications.show({
          color: "green", title: "Draft saved",
          message: "Nothing has been sent yet. Submit when you are ready.",
        });
      },
      onError: (e) => notifications.show({
        color: "red", title: "Could not save the draft",
        message: errorMessage(e),
      }),
    });
  }

  function send() {
    if (!draftId) return;
    submit.mutate({ id: draftId }, {
      onSuccess: () => {
        setDraftId(null);
        setPurpose("");
        setStart("");
        setEnd("");
        notifications.show({
          color: "green", title: "Submitted",
          message: "Your leave request is now with the authority that reviews it.",
        });
      },
      onError: (e) => notifications.show({
        color: "red", title: "Could not submit",
        message: errorMessage(e),
      }),
    });
  }

  return (
    <Container size="lg">
      <PageHeader
        title="Apply for Leave"
        subtitle="Save a draft first — nobody is notified until you submit."
      />

      {config.isError && <ErrorState error={config.error} />}

      <Stack gap="lg">
        <FormSection title="Leave details">
          <Select
            label="Leave type"
            data={LEAVE_CATEGORIES.map((c) => ({
              value: c,
              label: CATEGORY_LABELS[c],
              disabled: allowed.length > 0 && !allowed.includes("faculty")
                && !allowed.includes("staff") && !allowed.includes(c),
            }))}
            value={category}
            onChange={(v) => {
              setCategory((v as LeaveCategory) ?? "CASUAL");
              if (!(HALF_DAY_CATEGORIES.includes(v as LeaveCategory))) {
                setHalfDay(false);
              }
            }}
            allowDeselect={false}
          />

          <Group grow>
            <TextInput type="date" label="From" value={start}
                       onChange={(e) => setStart(e.currentTarget.value)} />
            <TextInput type="date" label="To" value={end}
                       onChange={(e) => setEnd(e.currentTarget.value)} />
          </Group>

          {halfDayAllowed && (
            <Switch
              label="Half day" checked={halfDay}
              onChange={(e) => setHalfDay(e.currentTarget.checked)}
            />
          )}
          {halfDayAllowed && halfDay && (
            <Select label="Which half" value={half} onChange={setHalf}
                    data={[{ value: "morning", label: "Morning" },
                           { value: "afternoon", label: "Afternoon" }]} />
          )}

          <Textarea
            label="Reason for leave" autosize minRows={2} value={purpose}
            onChange={(e) => setPurpose(e.currentTarget.value)}
            placeholder="One line is enough."
          />

          <NumberInput
            label="Medical evidence reference (where applicable)"
            description="A reference, not an upload — ELM stores the pointer."
            value={evidence}
            onChange={(v) => setEvidence(String(v ?? ""))}
            hideControls
          />
        </FormSection>

        <FormSection title="Station leave">
          <Alert icon={<FaInfoCircle />} color="blue" variant="light">
            Station Leave is requested inside this application, not separately.
          </Alert>
          <Checkbox
            label="I need station leave arrangements" checked={station}
            onChange={(e) => setStation(e.currentTarget.checked)}
          />
          {station && (
            <Textarea
              label="Arrangements" autosize minRows={2} value={stationDetails}
              onChange={(e) => setStationDetails(e.currentTarget.value)}
              placeholder="Who covers, and how."
            />
          )}
        </FormSection>

        <FormSection title="What happens next">
          <Stack gap={6}>
            <Text size="sm">
              {halfDayAllowed && halfDay
                ? "A half day is recorded as 0.5 day."
                : continuous
                  ? "This type is counted continuously, so weekends and closed holidays are excluded."
                  : "This type excludes weekends and applicable closed holidays."}
            </Text>
            {vacationOnly && (
              <Text size="sm">
                Vacation Leave can only be taken inside a published vacation period.
              </Text>
            )}
            <Text size="sm">
              {establishment
                ? "Your Unit Head records a recommendation, then the Establishment routes it to the Sanctioning Authority."
                : "Your Unit Head records a recommendation, then it goes to the Sanctioning Authority."}
            </Text>
          </Stack>

          <Group justify="space-between" mt="md">
            <Button variant="default" onClick={makeDraft}
                    loading={create.isPending} disabled={!ready}>
              Save draft
            </Button>
            <Button onClick={send} loading={submit.isPending} disabled={!draftId}>
              Submit for approval
            </Button>
          </Group>
          {draftId && (
            <Text size="xs" c="dimmed" mt="xs">
              Draft #{draftId} saved. Submit it to notify the authority.
            </Text>
          )}
        </FormSection>
      </Stack>
    </Container>
  );
}