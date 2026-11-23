import { useState } from "react";
import { Button, Stack, Text } from "@mantine/core";

import { FormModal } from "../../../../ui/components/FormModal";
import { useChangeLeadership } from "../../api/hooks";
import type { LedClub } from "../../api/types";
import { PersonPicker } from "../PersonPicker";
import { done } from "../toasts";

export function LeadershipPanel({ club }: { club: LedClub }) {
  const [changing, setChanging] = useState(false);
  return (
    <Stack align="flex-start">
      <Text size="sm">
        Handing over replaces both leaders at once. You keep access only if you are one of them.
      </Text>
      <Button onClick={() => setChanging(true)}>Change leadership</Button>
      {changing && <LeadershipModal club={club} onClose={() => setChanging(false)} />}
    </Stack>
  );
}

function LeadershipModal({ club, onClose }: { club: LedClub; onClose: () => void }) {
  const change = useChangeLeadership();
  const [coordinator, setCoordinator] = useState<number | null>(null);
  const [coCoordinator, setCoCoordinator] = useState<number | null>(null);
  return (
    <FormModal
      opened onClose={onClose} title="Change leadership" subtitle={club.name}
      submitLabel="Replace leaders" danger submitting={change.isPending} error={change.error}
      disabled={coordinator === null || coCoordinator === null}
      disabledReason="Choose both new leaders."
      onSubmit={() => coordinator !== null && coCoordinator !== null && change.mutate({
        id: club.id, coordinator_id: coordinator, co_coordinator_id: coCoordinator,
      }, {
        onSuccess: () => {
          done("Leadership changed", `${club.name} has new leaders.`);
          onClose();
        },
      })}
    >
      <Stack gap="md">
        <PersonPicker label="New coordinator" kind="student" value={coordinator}
          onChange={setCoordinator} />
        <PersonPicker label="New co-coordinator" kind="student" value={coCoordinator}
          onChange={setCoCoordinator} />
      </Stack>
    </FormModal>
  );
}
