import { useState } from "react";
import {
  Alert, Button, Card, Divider, Group, Select, Stack, Text, TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { useRecordVerifiedLeaveCredit } from "../api/hooks";
import type { VerifiedLeaveCreditInput } from "../api/types";

const leaveTypes: VerifiedLeaveCreditInput["leave_type"][] = [
  "Casual", "Restricted", "Medical", "Earned", "Vacation", "Sabbatical",
];

export function LeaveCreditManagement() {
  const { can } = useAuth();
  const [expanded, setExpanded] = useState(false);
  const [userId, setUserId] = useState("");
  const [leaveType, setLeaveType] = useState<VerifiedLeaveCreditInput["leave_type"]>("Casual");
  const [quantity, setQuantity] = useState("");
  const [evidence, setEvidence] = useState("");
  const credit = useRecordVerifiedLeaveCredit();
  if (!can("hreis.balance.manage")) return null;

  function submit() {
    const employee = Number(userId);
    const days = Number(quantity);
    if (!Number.isSafeInteger(employee) || employee <= 0 || !Number.isFinite(days) || days <= 0
      || !evidence.trim()) {
      notifications.show({ position: "top-center",
        color: "red", title: "Invalid credit",
        message: "Provide a valid employee ID, positive number of days and evidence reference.",
      });
      return;
    }
    credit.mutate({
      user_id: employee,
      leave_type: leaveType,
      quantity,
      evidence_reference: evidence.trim(),
    }, {
      onSuccess: () => {
        notifications.show({ position: "top-center",
          color: "green", title: "Verified leave credit recorded",
          message: "An immutable ledger credit and HR audit event were created.",
        });
        setExpanded(false);
        setQuantity("");
        setEvidence("");
      },
      onError: (error) => notifications.show({ position: "top-center",
        color: "red", title: "Credit was not recorded", message: errorMessage(error),
      }),
    });
  }

  return (
    <Stack mt="xl">
      <Divider label="Verified leave-balance credits" labelPosition="left" />
      <Alert color="yellow" title="Only verified institutional entitlements">
        HR-EIS does not assign leave quotas automatically. Record only a positive
        credit supported by a reviewed institutional source reference. Existing
        ledger transactions are immutable.
      </Alert>
      <Group>
        <Button variant="light" onClick={() => setExpanded((value) => !value)}>
          {expanded ? "Close leave-credit form" : "Record verified leave credit"}
        </Button>
      </Group>
      {expanded && <Card withBorder>
        <Stack>
          <Text size="sm" c="dimmed">
            The employee must already exist in the IAM directory and official HR service records.
          </Text>
          <TextInput label="Employee directory ID" required value={userId}
            onChange={(event) => setUserId(event.currentTarget.value)} />
          <Select label="Leave type" required data={leaveTypes} value={leaveType}
            onChange={(value) => setLeaveType(leaveTypes.find((item) => item === value) ?? "Casual")} />
          <TextInput label="Verified credit (days)" required value={quantity}
            onChange={(event) => setQuantity(event.currentTarget.value)} />
          <TextInput label="Approved evidence or register reference" required
            value={evidence}
            onChange={(event) => setEvidence(event.currentTarget.value)} />
          <Button loading={credit.isPending} onClick={submit}>
            Record immutable leave credit
          </Button>
        </Stack>
      </Card>}
    </Stack>
  );
}
