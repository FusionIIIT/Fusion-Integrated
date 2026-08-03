import { useState } from "react";
import {
  Alert, Badge, Button, Card, Container, Group, List, Stack, Text, Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  FaCheckCircle, FaExclamationTriangle, FaInfoCircle, FaTimesCircle,
} from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useMyConductRecord, useMyRegistrations, useOptOut, useRegister,
  useRegistrationTerms, useSeasons,
} from "../api/hooks";
import type { RegistrationTerms } from "../api/hooks";

/** Rule 1 makes this the gate on everything else, so the page leads with where
 *  the student stands and what, if anything, they can do about it. */
export default function RegistrationPage() {
  const seasons = useSeasons();
  const active = seasons.data?.find((s) => s.is_active)?.season;
  const registrations = useMyRegistrations();
  const terms = useRegistrationTerms(active);
  const register = useRegister();
  const optOut = useOptOut();

  const [confirmOptOut, setConfirmOptOut] = useState(false);
  const [reason, setReason] = useState("");

  const current = registrations.data?.results?.find((r) => r.season === active);

  if (registrations.error) {
    return <Container size="md"><ErrorState error={registrations.error} /></Container>;
  }

  if (!active) {
    return (
      <Container size="md">
        <PageHeader title="Season Registration" />
        <Alert variant="light" color="gray" icon={<FaInfoCircle />}>
          No placement season is open at the moment.
        </Alert>
      </Container>
    );
  }

  function submitRegister() {
    register.mutate(active!, {
      onSuccess: () => notifications.show({
        color: "green", title: "You are registered",
        message: "You can now apply to postings you are eligible for.",
      }),
      onError: (e) => notifications.show({
        color: "red", title: "Could not register", message: errorMessage(e),
      }),
    });
  }

  function submitOptOut() {
    optOut.mutate({ season: active!, reason }, {
      onSuccess: () => {
        notifications.show({
          color: "orange", title: "You have withdrawn",
          message: "Coming back needs the re-registration fee, once only.",
        });
        setConfirmOptOut(false);
        setReason("");
      },
      onError: (e) => notifications.show({
        color: "red", title: "Could not withdraw", message: errorMessage(e),
      }),
    });
  }

  return (
    <Container size="md">
      <PageHeader
        title="Season Registration"
        subtitle={`Placement season ${active}`}
        action={current ? <StatusBadge status={current.status} /> : undefined}
      />

      {current?.status === "registered" && (
        <Card padding="lg" mb="md">
          <Group justify="space-between" align="flex-start" wrap="nowrap">
            <Stack gap={4}>
              <Group gap="xs">
                <FaCheckCircle color="var(--mantine-color-green-6)" />
                <Text fw={600}>You are registered for {active}</Text>
              </Group>
              <Text size="sm" c="dimmed">
                {current.registered_late
                  ? "Registered late, against the fee recorded by the Placement Cell."
                  : "Registered within the deadline."}
              </Text>
            </Stack>
            <Button
              variant="default" color="red" size="xs"
              onClick={() => setConfirmOptOut(true)}
            >
              Withdraw
            </Button>
          </Group>
        </Card>
      )}

      {current?.status === "debarred" && (
        <Alert
          variant="light" color="red" icon={<FaTimesCircle />} mb="md"
          title="A debarment is in force"
        >
          <Text size="sm">{current.debarred_reason || "Contact the Placement Cell."}</Text>
        </Alert>
      )}

      {current?.status !== "registered" && terms.data && (
        <TermsCard
          terms={terms.data} season={active}
          onRegister={submitRegister} busy={register.isPending}
        />
      )}

      <ConductRecord />

      <Card padding="lg">
        <Text fw={600} mb="xs">What registration means</Text>
        <List size="sm" spacing="xs" c="dimmed">
          <List.Item>
            Only registered students may appear for campus recruitment (rule 1).
          </List.Item>
          <List.Item>
            Consenting to a company and then not appearing may cost you the next
            two drives (rule 19).
          </List.Item>
          <List.Item>
            Withdrawing is reversible once, on the re-registration fee (rule 21).
          </List.Item>
          <List.Item>
            From September, appearing becomes mandatory for eligible unplaced
            students (rule 6).
          </List.Item>
        </List>
      </Card>

      <FormModal
        opened={confirmOptOut} onClose={() => setConfirmOptOut(false)}
        title="Withdraw from placement"
        subtitle={`Season ${active}`}
        onSubmit={submitOptOut} submitLabel="Withdraw" danger
        submitting={optOut.isPending} size="md"
      >
        <Stack gap="md">
          <Alert variant="light" color="orange"
            icon={<FaExclamationTriangle />}>
            <Text size="sm">
              Rule 21 allows you to re-register <b>once</b>, on payment of the
              re-registration fee and at the Chairperson&apos;s discretion.
              After that the route closes for good.
            </Text>
          </Alert>
          <Textarea
            label="Reason" autosize minRows={3} value={reason}
            onChange={(e) => setReason(e.currentTarget.value)}
            placeholder="Higher studies, off-campus offer, …"
          />
        </Stack>
      </FormModal>
    </Container>
  );
}

const INCIDENT_LABELS: Record<string, string> = {
  consent_failure: "Did not appear after consenting (rule 19)",
  code_of_conduct: "Code of conduct (rule 21)",
  misrepresentation: "False resume or unfair means (rule 18)",
};

/** A student's own conduct record. Shown because rule 19 allows a waiver and
 *  rule 21 leaves a sanction to the Chairperson — neither is contestable if the
 *  student cannot read what is on file. */
function ConductRecord() {
  const { data } = useMyConductRecord();
  const rows = data?.results ?? [];
  if (!rows.length) return null;

  return (
    <Card padding="lg" mb="md">
      <Text fw={600} mb={2}>Conduct record</Text>
      <Text size="xs" c="dimmed" mb="sm">
        Contact the Placement Cell if you believe any of this is in error.
      </Text>
      <Stack gap="sm">
        {rows.map((incident) => (
          <Group key={incident.id} justify="space-between" align="flex-start"
            wrap="nowrap">
            <Stack gap={2} style={{ minWidth: 0 }}>
              <Text size="sm" fw={500}>
                {INCIDENT_LABELS[incident.kind] ?? incident.kind}
              </Text>
              <Text size="xs" c="dimmed">{incident.note}</Text>
              {incident.waived && (
                <Text size="xs" c="teal">
                  Waived — {incident.waived_reason}
                </Text>
              )}
            </Stack>
            <Badge
              variant="light" size="sm"
              color={incident.waived ? "teal" : "orange"}
            >
              {incident.waived ? "waived" : "on record"}
            </Badge>
          </Group>
        ))}
      </Stack>
    </Card>
  );
}

function StatusBadge({ status }: { status: string }) {
  const tone = status === "registered" ? "green"
    : status === "debarred" ? "red" : "gray";
  return <Badge color={tone} variant="light">{status.replace("_", " ")}</Badge>;
}

/** The four routes the server can return. `late` and `reregister` are not
 *  refusals — they are real paths that go through the Placement Cell, so the
 *  copy says what to do rather than just saying no. */
function TermsCard({ terms, season, onRegister, busy }: {
  terms: RegistrationTerms;
  season: string;
  onRegister: () => void;
  busy: boolean;
}) {
  if (terms.route === "open") {
    return (
      <Card padding="lg" mb="md">
        <Stack gap="sm">
          <Text fw={600}>Register for {season}</Text>
          <Text size="sm" c="dimmed">{terms.message}</Text>
          <Group>
            <Button onClick={onRegister} loading={busy}>
              Register for this season
            </Button>
          </Group>
        </Stack>
      </Card>
    );
  }

  const needsOffice = terms.route === "late" || terms.route === "reregister";
  return (
    <Alert
      variant="light" color={needsOffice ? "orange" : "red"}
      icon={needsOffice ? <FaExclamationTriangle /> : <FaTimesCircle />}
      title={needsOffice ? "Registration needs the Placement Cell" : "You cannot register"}
      mb="md"
    >
      <Text size="sm">{terms.message}</Text>
      {terms.fee > 0 && (
        <Text size="sm" mt={6}>
          Pay ₹{terms.fee} to the Institute account and take the challan to the
          Placement Cell — they will complete your registration here.
        </Text>
      )}
    </Alert>
  );
}
