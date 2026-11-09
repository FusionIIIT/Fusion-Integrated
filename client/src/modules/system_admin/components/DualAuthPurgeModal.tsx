import { useState } from "react";
import {
  Alert,
  Button,
  Group,
  Radio,
  Stack,
  Text,
  Textarea,
  ThemeIcon,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaExclamationTriangle, FaTrash } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { FormModal } from "../../../ui/components/FormModal";
import { useAuthorizePurge, useRequestPurge } from "../api/hooks";
import type { ArchivedUserRecord, PurgeRequest } from "../api/types";

export function DualAuthPurgeModal({
  archivedUser,
  purgeRequest,
  opened,
  onClose,
}: {
  archivedUser?: ArchivedUserRecord | null;
  purgeRequest?: PurgeRequest | null;
  opened: boolean;
  onClose: () => void;
}) {
  const { session } = useAuth();
  const requestPurge = useRequestPurge();
  const authorizePurge = useAuthorizePurge();

  const [reason, setReason] = useState("");
  const [decision, setDecision] = useState<"approve" | "reject">("approve");
  const [comments, setComments] = useState("");

  const isITHead =
    session?.roles?.includes("it_head") ||
    session?.roles?.includes("director") ||
    session?.active_role === "it_head";

  const isAuthorizing = Boolean(purgeRequest && isITHead);

  const handleSubmit = () => {
    if (isAuthorizing && purgeRequest) {
      authorizePurge.mutate(
        {
          id: purgeRequest.id,
          payload: {
            approved: decision === "approve",
            comments: comments.trim(),
          },
        },
        {
          onSuccess: (data) => {
            notifications.show({
              color: decision === "approve" ? "red" : "blue",
              title: decision === "approve" ? "Purge Authorized" : "Purge Rejected",
              message: `Purge request #${data.id} has been ${data.status}.`,
            });
            onClose();
          },
          onError: (err) => {
            notifications.show({
              color: "red",
              title: "Decision Failed",
              message: errorMessage(err),
            });
          },
        },
      );
    } else if (archivedUser) {
      if (!reason.trim()) {
        notifications.show({
          color: "red",
          title: "Reason Required",
          message: "A justification is mandatory for permanent purge requests.",
        });
        return;
      }

      requestPurge.mutate(
        {
          archive_id: archivedUser.basic_user_id,
          reason: reason.trim(),
        },
        {
          onSuccess: () => {
            notifications.show({
              color: "yellow",
              title: "Purge Request Submitted",
              message:
                "Request is now pending IT Head dual-authorization (BR-SA-022).",
            });
            setReason("");
            onClose();
          },
          onError: (err) => {
            notifications.show({
              color: "red",
              title: "Request Failed",
              message: errorMessage(err),
            });
          },
        },
      );
    }
  };

  return (
    <FormModal
      opened={opened}
      onClose={onClose}
      title={isAuthorizing ? "Dual-Authorization Decision" : "Request Permanent Purge"}
      subtitle="Critical Operation — Dual-Authorization Governance (CW-SA-01)"
      onSubmit={handleSubmit}
      submitting={requestPurge.isPending || authorizePurge.isPending}
      submitLabel={
        isAuthorizing
          ? decision === "approve"
            ? "Authorize Permanent Purge"
            : "Reject Request"
          : "Submit for IT Head Approval"
      }
      danger={decision === "approve" || !isAuthorizing}
      size="md"
    >
      <Stack gap="md">
        <Alert
          icon={<FaExclamationTriangle size={18} />}
          color="red"
          title="IRREVERSIBLE DATA LOSS WARNING"
        >
          Permanent purge is non-recoverable. All personal identifying data,
          credentials, and system records for this account will be permanently
          destroyed.
        </Alert>

        {isAuthorizing && purgeRequest ? (
          <Stack gap="sm">
            <Text size="sm">
              <strong>Purge Request #{purgeRequest.id}</strong>
            </Text>
            <Text size="xs" c="dimmed">
              Initiator Reason: {purgeRequest.request_reason}
            </Text>

            <Radio.Group
              label="Dual-Authorization Verdict"
              value={decision}
              onChange={(v) => setDecision(v as "approve" | "reject")}
              required
            >
              <Group mt="xs">
                <Radio value="approve" label="Approve & Purge Immediately" color="red" />
                <Radio value="reject" label="Reject Purge Request" color="gray" />
              </Group>
            </Radio.Group>

            <Textarea
              label="IT Head Comments / Reference"
              placeholder="Record approval reference number or reason for rejection..."
              value={comments}
              onChange={(e) => setComments(e.currentTarget.value)}
              rows={2}
            />
          </Stack>
        ) : (
          archivedUser && (
            <Stack gap="sm">
              <Text size="sm">
                Target User: <strong>{archivedUser.username}</strong> (
                {archivedUser.institute_id})
              </Text>
              <Text size="xs" c="dimmed">
                Archived At: {new Date(archivedUser.archived_at).toLocaleString()}
              </Text>

              <Textarea
                label="Statutory / Institutional Justification"
                placeholder="Reason for requiring permanent purge (required)..."
                value={reason}
                onChange={(e) => setReason(e.currentTarget.value)}
                required
                rows={3}
              />
            </Stack>
          )
        )}
      </Stack>
    </FormModal>
  );
}
