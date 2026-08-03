import { useState } from "react";
import {
  Alert, Badge, Button, Card, Group, Select, Stack, Text, Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  FaCheckCircle, FaExclamationTriangle, FaFileUpload, FaInfoCircle,
} from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { FormModal } from "../../../ui/components/FormModal";
import {
  useDeclareNotJoining, useMyClearance, useMyDocuments, useMyRecords,
  useSubmitOfferLetter,
} from "../api/hooks";
import type { PlacementRecordRow } from "../api/hooks";

/** What rules 22 and 24 ask of a student once they have accepted an offer.
 *
 *  Rule 24 withholds the no-dues certificate until the signed letter is in, so
 *  the hold and the way to release it have to sit together — a block with no
 *  visible remedy is worse than no block at all. */
export function PlacementRecordCard() {
  const records = useMyRecords();
  const clearance = useMyClearance();
  const submit = useSubmitOfferLetter();
  const declare = useDeclareNotJoining();
  const documents = useMyDocuments();

  const [attaching, setAttaching] = useState<PlacementRecordRow | null>(null);
  const [documentId, setDocumentId] = useState<string | null>(null);
  const [declaring, setDeclaring] = useState<PlacementRecordRow | null>(null);
  const [reason, setReason] = useState("");

  const rows = records.data?.results ?? [];
  if (!rows.length) return null;

  // Rule 24 only accepts a document filed as an offer letter.
  const letters = (documents.data?.results ?? [])
    .filter((d) => d.kind === "offer_letter")
    .map((d) => ({ value: String(d.id), label: d.title || "Offer letter" }));

  function doSubmit() {
    if (!attaching || !documentId) return;
    submit.mutate(
      { recordId: attaching.id, document_id: Number(documentId) },
      {
        onSuccess: () => {
          notifications.show({
            color: "green", title: "Offer letter recorded",
            message: "Rule 24's hold on your no-dues certificate is released.",
          });
          setAttaching(null);
          setDocumentId(null);
        },
        onError: (e) => notifications.show({
          color: "red", title: "Could not record it", message: errorMessage(e),
        }),
      },
    );
  }

  function doDeclare() {
    if (!declaring) return;
    declare.mutate(
      { recordId: declaring.id, reason },
      {
        onSuccess: (result) => {
          notifications.show({
            color: result.is_late ? "orange" : "green",
            title: result.is_late ? "Recorded, but late" : "Recorded",
            message: result.message,
          });
          setDeclaring(null);
          setReason("");
        },
        onError: (e) => notifications.show({
          color: "red", title: "Could not record it", message: errorMessage(e),
        }),
      },
    );
  }

  return (
    <>
      {clearance.data && !clearance.data.cleared && (
        <Alert
          variant="light" color="orange" icon={<FaExclamationTriangle />} mb="md"
          title="Your no-dues certificate is on hold"
        >
          <Text size="sm">{clearance.data.message}</Text>
        </Alert>
      )}

      <Card padding="lg" mb="md">
        <Text fw={600} mb="sm">Your placement</Text>
        <Stack gap="md">
          {rows.map((record) => (
            <Group
              key={record.id} justify="space-between" align="flex-start"
              wrap="nowrap"
            >
              <Stack gap={4} style={{ minWidth: 0 }}>
                <Group gap="xs" wrap="nowrap">
                  <Text fw={600}>{record.company?.name ?? "—"}</Text>
                  {record.source === "off_campus" && (
                    <Badge variant="light" size="sm" color="gray">off campus</Badge>
                  )}
                  {record.offer_letter_submitted ? (
                    <Badge variant="light" size="sm" color="green"
                      leftSection={<FaCheckCircle size={9} />}>
                      letter on file
                    </Badge>
                  ) : (
                    <Badge variant="light" size="sm" color="orange">
                      letter pending
                    </Badge>
                  )}
                </Group>
                <Text size="xs" c="dimmed">
                  {record.kind.toUpperCase()}
                  {record.ctc_lpa ? ` · ${record.ctc_lpa} LPA` : ""}
                </Text>
                {record.not_joining_declared_at && (
                  <Text size="xs" c={record.not_joining_was_late ? "orange" : "dimmed"}>
                    Not joining — {record.not_joining_reason}
                    {record.not_joining_was_late
                      ? " (declared after the rule 22 cut-off)" : ""}
                  </Text>
                )}
              </Stack>
              <Group gap="xs" wrap="nowrap">
                {!record.offer_letter_submitted && (
                  <Button
                    size="xs" variant="default"
                    leftSection={<FaFileUpload size={11} />}
                    onClick={() => setAttaching(record)}
                  >
                    Submit signed letter
                  </Button>
                )}
                {!record.not_joining_declared_at && (
                  <Button
                    size="xs" variant="subtle" color="orange"
                    onClick={() => setDeclaring(record)}
                  >
                    Not joining
                  </Button>
                )}
              </Group>
            </Group>
          ))}
        </Stack>
      </Card>

      <FormModal
        opened={attaching != null} onClose={() => setAttaching(null)}
        title="Submit the signed offer letter"
        subtitle={attaching?.company?.name}
        onSubmit={doSubmit} submitLabel="Record it" size="md"
        submitting={submit.isPending} disabled={!documentId}
        disabledReason="Choose the offer letter you linked on your profile."
      >
        <Stack gap="md">
          <Alert variant="light" color="blue" icon={<FaInfoCircle />}>
            <Text size="sm">
              Rule 24 withholds the no-dues certificate until the signed copy is
              with the Placement Cell.
            </Text>
          </Alert>
          <Select
            label="Offer letter" data={letters}
            value={documentId} onChange={setDocumentId}
            placeholder={letters.length
              ? "Select" : "Link one on My Profile first"}
            disabled={!letters.length}
            description="Add it under Documents on your profile, as an offer letter."
          />
        </Stack>
      </FormModal>

      <FormModal
        opened={declaring != null} onClose={() => setDeclaring(null)}
        title="Tell the Placement Cell you will not join"
        subtitle={declaring?.company?.name}
        onSubmit={doDeclare} submitLabel="Inform the Cell" size="md"
        submitting={declare.isPending} disabled={!reason.trim()}
        disabledReason="Rule 22 asks for the reason."
      >
        <Stack gap="md">
          <Alert variant="light" color="orange" icon={<FaExclamationTriangle />}>
            <Text size="sm">
              Rule 22 asks you to inform the Cell on or before the cut-off.
              Telling them late, or not at all, may be referred to the institute.
            </Text>
            <Text size="sm" mt={6} c="dimmed">
              This does not remove the offer-letter requirement — the acceptance
              still stands on your record.
            </Text>
          </Alert>
          <Textarea
            label="Reason" autosize minRows={3} value={reason}
            onChange={(e) => setReason(e.currentTarget.value)}
            placeholder="Higher studies, or another genuine reason"
          />
        </Stack>
      </FormModal>
    </>
  );
}
