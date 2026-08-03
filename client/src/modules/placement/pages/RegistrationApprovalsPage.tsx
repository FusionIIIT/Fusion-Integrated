import { useState } from "react";
import {
  Alert, Button, Card, Container, Group, NumberInput, Select, Stack, Text,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaInfoCircle } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { Field, FormRow, FormSection } from "../../../ui/components/FormSection";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useApproveLate, useReRegister, useSeasons } from "../api/hooks";

const ROUTES = [
  { value: "late", label: "Late registration (rule 20)" },
  { value: "reregister", label: "Re-registration (rule 21)" },
];

/** Rules 20 and 21 both require the office to have seen a challan, which is why
 *  these are staff actions rather than something a student can self-serve. */
export default function RegistrationApprovalsPage() {
  const seasons = useSeasons();
  const approveLate = useApproveLate();
  const reRegister = useReRegister();

  const active = seasons.data?.find((s) => s.is_active)?.season ?? null;
  const [season, setSeason] = useState<string | null>(null);
  const [route, setRoute] = useState<string | null>("late");
  const [userId, setUserId] = useState<number | string>("");
  const [reference, setReference] = useState("");

  const chosenSeason = season ?? active;
  const busy = approveLate.isPending || reRegister.isPending;
  const ready = Boolean(chosenSeason) && userId !== "" && reference.trim();

  function submit() {
    if (!ready || !chosenSeason) return;
    const body = {
      season: chosenSeason,
      user_id: Number(userId),
      fee_reference: reference.trim(),
    };
    const mutation = route === "reregister" ? reRegister : approveLate;
    mutation.mutate(body, {
      onSuccess: (registration) => {
        notifications.show({
          color: "green", title: "Registration completed",
          message: `Student ${body.user_id} is ${registration.status}.`,
        });
        setUserId("");
        setReference("");
      },
      onError: (e) => notifications.show({
        color: "red", title: "Could not complete", message: errorMessage(e),
      }),
    });
  }

  return (
    <Container size="md">
      <PageHeader
        title="Registrations"
        subtitle="Late registrations and re-registrations"
      />

      <Alert variant="light" color="blue" icon={<FaInfoCircle />} mb="md">
        <Text size="sm">
          PCMS records the payment reference; it does not take payment. Enter the
          challan or receipt number the student produced — rules 20 and 21 both
          require a copy to be submitted.
        </Text>
      </Alert>

      <Card padding="lg">
        <FormSection
          first title="Complete a registration"
          hint="Rule 21's re-registration is available once per student, and the
                server refuses a second attempt."
        >
          <Stack gap="md">
            <FormRow>
              <Field span={6}>
                <Select
                  label="Season" data={(seasons.data ?? []).map((s) => ({
                    value: s.season,
                    label: s.is_active ? `${s.season} (active)` : s.season,
                  }))}
                  value={chosenSeason} onChange={setSeason}
                  allowDeselect={false}
                  placeholder={seasons.isPending ? "Loading…" : "Select"}
                />
              </Field>
              <Field span={6}>
                <Select
                  label="Route" data={ROUTES} value={route} onChange={setRoute}
                  allowDeselect={false}
                />
              </Field>
              <Field span={6}>
                <NumberInput
                  label="Student user id" value={userId} onChange={setUserId}
                  min={1} hideControls placeholder="e.g. 4098"
                  description="From the CPI directory or the applications list"
                />
              </Field>
              <Field span={6}>
                <TextInput
                  label="Challan / receipt number" value={reference}
                  onChange={(e) => setReference(e.currentTarget.value)}
                  placeholder="CH-2026-114"
                />
              </Field>
            </FormRow>
            <Group justify="flex-end">
              <Button onClick={submit} loading={busy} disabled={!ready}>
                Complete registration
              </Button>
            </Group>
          </Stack>
        </FormSection>
      </Card>
    </Container>
  );
}
