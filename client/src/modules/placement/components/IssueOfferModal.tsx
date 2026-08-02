import { useState } from "react";
import { Alert, NumberInput, Stack, Text } from "@mantine/core";
import { DateTimePicker } from "@mantine/dates";
import { notifications } from "@mantine/notifications";
import { FaInfoCircle } from "react-icons/fa";

import { FormModal } from "../../../ui/components/FormModal";
import { errorMessage } from "../../../lib/http";
import { useIssueOffer } from "../api/hooks";
import type { Application } from "../api/types";

export function IssueOfferModal({ application, onClose }: {
  application: Application | null;
  onClose: () => void;
}) {
  const issue = useIssueOffer();
  const [ctc, setCtc] = useState<number | string>("");
  const [respondBy, setRespondBy] = useState<Date | null>(null);

  function submit() {
    if (!application) return;
    issue.mutate(
      {
        application_id: application.id,
        ctc_lpa: ctc === "" ? undefined : String(ctc),
        respond_by: respondBy ? respondBy.toISOString() : undefined,
      },
      {
        onSuccess: () => {
          notifications.show({
            color: "green", title: "Offer issued",
            message: "The candidate has been notified with the deadline.",
          });
          setCtc(""); setRespondBy(null);
          onClose();
        },
        onError: (e) => notifications.show({
          color: "red", title: "Could not issue offer", message: errorMessage(e),
        }),
      },
    );
  }

  return (
    <FormModal
      opened={application != null} onClose={onClose}
      title="Issue an offer"
      subtitle={application?.candidate?.name
        ? `To ${application.candidate.name} for ${application.posting?.title}`
        : undefined}
      onSubmit={submit} submitLabel="Issue offer"
      submitting={issue.isPending} error={issue.error}
    >
      <Stack gap="md">
        <NumberInput
          label="CTC (LPA)" value={ctc} onChange={setCtc}
          decimalScale={2} min={0}
          description="Leave blank to use the posting's CTC"
        />
        <DateTimePicker
          label="Respond by" value={respondBy} onChange={setRespondBy}
          description="Leave blank to use the season's default window"
        />
        <Alert variant="light" color="blue" icon={<FaInfoCircle />}>
          <Text size="sm">
            Every offer carries a response deadline. If the candidate does not
            answer in time the offer expires automatically, which releases them
            back into the pool rather than leaving them blocked indefinitely.
          </Text>
        </Alert>
      </Stack>
    </FormModal>
  );
}
