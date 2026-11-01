import { useState } from "react";
import {
  Modal,
  TextInput,
  Select,
  NumberInput,
  Stack,
  Button,
  Group,
  Textarea,
  Text,
  Alert,
} from "@mantine/core";
import {
  useArchiveUser,
  useArchiveHistoricalData,
  useCreatePurgeRequest,
  useAuthorizePurgeRequest,
  useRestoreArchivedUser,
  useRestoreHistoricalData,
} from "../api/hooks";
import type { ArchivedHistoricalDataItem, PermanentPurgeRequestItem } from "../api/types";
import { errorMessage } from "../../../lib/http";

export function ArchiveUserModal({
  opened,
  onClose,
}: {
  opened: boolean;
  onClose: () => void;
}) {
  const [userId, setUserId] = useState("");
  const [retentionOption, setRetentionOption] = useState("standard_institutional");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);

  const archiveMutation = useArchiveUser();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await archiveMutation.mutateAsync({
        user_id: Number(userId),
        retention_option: retentionOption,
        reason,
      });
      onClose();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  return (
    <Modal opened={opened} onClose={onClose} title="Archive Deactivated User" size="md">
      <form onSubmit={handleSubmit}>
        <Stack gap="sm">
          {error && <Alert color="red">{error}</Alert>}
          <Text size="xs" c="dimmed">
            Note: User must be in "deactivated" status and have satisfied the minimum deactivation interval.
          </Text>
          <TextInput
            label="Internal User ID"
            placeholder="e.g. 1"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            required
          />
          <Select
            label="Institutional Retention Policy"
            data={[
              { value: "standard_institutional", label: "Standard Institutional (7 Years)" },
              { value: "alumni_permanent_records", label: "Alumni Academic Records (Permanent)" },
              { value: "regulatory_compliance_extended", label: "Extended Statutory Hold (15 Years)" },
            ]}
            value={retentionOption}
            onChange={(val) => setRetentionOption(val ?? "standard_institutional")}
            required
          />
          <Textarea
            label="Archival Justification"
            placeholder="State grounds for archival..."
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            required
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={onClose}>Cancel</Button>
            <Button type="submit" color="orange" loading={archiveMutation.isPending}>Execute Archival</Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}

export function RestoreUserModal({
  userId,
  instituteId,
  opened,
  onClose,
}: {
  userId: number;
  instituteId: string;
  opened: boolean;
  onClose: () => void;
}) {
  const [authRef, setAuthRef] = useState("");
  const [error, setError] = useState<string | null>(null);

  const restoreMutation = useRestoreArchivedUser(userId);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await restoreMutation.mutateAsync({ restoration_authorization_ref: authRef });
      onClose();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  return (
    <Modal opened={opened} onClose={onClose} title={`Restore Archived User: ${instituteId}`} size="md">
      <form onSubmit={handleSubmit}>
        <Stack gap="sm">
          {error && <Alert color="red">{error}</Alert>}
          <Text size="sm">
            Restoration is only permissible if the reversibility window has not elapsed.
          </Text>
          <TextInput
            label="Administrative Authorization Reference (Mandatory)"
            placeholder="e.g. DIR/RESTORE/2026/01"
            value={authRef}
            onChange={(e) => setAuthRef(e.target.value)}
            required
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={onClose}>Cancel</Button>
            <Button type="submit" color="green" loading={restoreMutation.isPending}>Restore Account</Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}

export function ArchiveDataModal({
  opened,
  onClose,
}: {
  opened: boolean;
  onClose: () => void;
}) {
  const [category, setCategory] = useState("system_audit_logs");
  const [startDate, setStartDate] = useState("2020-01-01");
  const [endDate, setEndDate] = useState("2020-12-31");
  const [recordCount, setRecordCount] = useState<number | string>(10000);
  const [storageSize, setStorageSize] = useState<number | string>(35000);
  const [backupRef, setBackupRef] = useState("");
  const [retentionYears, setRetentionYears] = useState<number | string>(7);
  const [error, setError] = useState<string | null>(null);

  const archiveMutation = useArchiveHistoricalData();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await archiveMutation.mutateAsync({
        category,
        date_range_start: startDate,
        date_range_end: endDate,
        record_count: Number(recordCount),
        storage_size_kb: Number(storageSize),
        backup_reference: backupRef,
        retention_years: Number(retentionYears),
      });
      onClose();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  return (
    <Modal opened={opened} onClose={onClose} title="Archive Historical Dataset Batch" size="md">
      <form onSubmit={handleSubmit}>
        <Stack gap="sm">
          {error && <Alert color="red">{error}</Alert>}
          <Select
            label="Dataset Category"
            data={[
              { value: "system_audit_logs", label: "System Audit Logs" },
              { value: "session_access_logs", label: "Session Access Logs" },
              { value: "past_cohort_admissions", label: "Past Cohort Admissions Metadata" },
              { value: "system_security_alerts", label: "Resolved Security Alerts" },
            ]}
            value={category}
            onChange={(val) => setCategory(val ?? "system_audit_logs")}
            required
          />
          <Group grow>
            <TextInput
              label="Date Range Start"
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              required
            />
            <TextInput
              label="Date Range End"
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              required
            />
          </Group>
          <Group grow>
            <NumberInput
              label="Estimated Record Count"
              value={recordCount}
              onChange={(val) => setRecordCount(val)}
              required
            />
            <NumberInput
              label="Storage Size (KB)"
              value={storageSize}
              onChange={(val) => setStorageSize(val)}
              required
            />
          </Group>
          <TextInput
            label="Mandatory Backup Reference Identifier"
            placeholder="e.g. S3://fusion-cold/logs-2020.tar.gz"
            value={backupRef}
            onChange={(e) => setBackupRef(e.target.value)}
            required
          />
          <NumberInput
            label="Retention Period (Years)"
            value={retentionYears}
            onChange={(val) => setRetentionYears(val)}
            min={1}
            max={25}
            required
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={onClose}>Cancel</Button>
            <Button type="submit" color="orange" loading={archiveMutation.isPending}>Archive Dataset</Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}

export function RestoreDataModal({
  batch,
  opened,
  onClose,
}: {
  batch: ArchivedHistoricalDataItem;
  opened: boolean;
  onClose: () => void;
}) {
  const [approvalRef, setApprovalRef] = useState("");
  const [error, setError] = useState<string | null>(null);

  const restoreMutation = useRestoreHistoricalData(batch.id);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await restoreMutation.mutateAsync({ approval_ref: approvalRef });
      onClose();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  return (
    <Modal opened={opened} onClose={onClose} title={`Restore Dataset: ${batch.category}`} size="md">
      <form onSubmit={handleSubmit}>
        <Stack gap="sm">
          {error && <Alert color="red">{error}</Alert>}
          <Text size="sm">
            Dataset Range: <b>{batch.date_range_start}</b> to <b>{batch.date_range_end}</b> ({batch.record_count} records)
          </Text>
          <TextInput
            label="Administrative Approval Reference"
            placeholder="e.g. AUDIT/RESTORE/2026/02"
            value={approvalRef}
            onChange={(e) => setApprovalRef(e.target.value)}
            required
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={onClose}>Cancel</Button>
            <Button type="submit" color="green" loading={restoreMutation.isPending}>Restore Dataset</Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}

export function PurgeRequestModal({
  opened,
  onClose,
}: {
  opened: boolean;
  onClose: () => void;
}) {
  const [targetType, setTargetType] = useState<"historical_data" | "archived_user">("historical_data");
  const [targetId, setTargetId] = useState("");
  const [reason, setReason] = useState("");
  const [regRef, setRegRef] = useState("");
  const [error, setError] = useState<string | null>(null);

  const purgeMutation = useCreatePurgeRequest();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await purgeMutation.mutateAsync({
        target_type: targetType,
        target_id: Number(targetId),
        reason,
        regulatory_authorization_ref: regRef,
      });
      onClose();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  return (
    <Modal opened={opened} onClose={onClose} title="Request Permanent Data Purge (Dual-Auth Gate 1)" size="md">
      <form onSubmit={handleSubmit}>
        <Stack gap="sm">
          {error && <Alert color="red">{error}</Alert>}
          <Alert color="orange">
            Dual Authorization Notice: Submission by Super Admin initiates a pending purge request. Permanent deletion will only occur upon secondary review and authorization by the IT Head.
          </Alert>
          <Select
            label="Purge Target Type"
            data={[
              { value: "historical_data", label: "Archived Historical Dataset" },
              { value: "archived_user", label: "Archived User Account (Non-Restorable)" },
            ]}
            value={targetType}
            onChange={(val) => setTargetType((val as "historical_data" | "archived_user") ?? "historical_data")}
            required
          />
          <TextInput
            label="Target Record ID"
            placeholder="e.g. 1"
            value={targetId}
            onChange={(e) => setTargetId(e.target.value)}
            required
          />
          <TextInput
            label="Regulatory / Legal Authorization Reference"
            placeholder="e.g. STATUTORY/PURGE/2026/01"
            value={regRef}
            onChange={(e) => setRegRef(e.target.value)}
            required
          />
          <Textarea
            label="Purge Justification"
            placeholder="State grounds for permanent destruction..."
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            required
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={onClose}>Cancel</Button>
            <Button type="submit" color="red" loading={purgeMutation.isPending}>Submit Purge Request</Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}

export function PurgeAuthorizeModal({
  request,
  opened,
  onClose,
}: {
  request: PermanentPurgeRequestItem;
  opened: boolean;
  onClose: () => void;
}) {
  const [decision, setDecision] = useState<"approve" | "reject">("approve");
  const [comments, setComments] = useState("");
  const [error, setError] = useState<string | null>(null);

  const authMutation = useAuthorizePurgeRequest(request.id);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await authMutation.mutateAsync({ decision, comments });
      onClose();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title="Dual-Authorization Decision (IT Head Gate 2)"
      size="md"
    >
      <form onSubmit={handleSubmit}>
        <Stack gap="sm">
          {error && <Alert color="red">{error}</Alert>}
          <Text size="sm">
            Target: <b>{request.target_summary}</b>
          </Text>
          <Text size="xs" c="dimmed">
            Requested by: {request.requested_by} | Regulatory Ref: {request.regulatory_authorization_ref}
          </Text>
          <Select
            label="IT Head Decision"
            data={[
              { value: "approve", label: "Approve Permanent Purge (Irreversible Destruction)" },
              { value: "reject", label: "Reject Purge (Retain in Archive)" },
            ]}
            value={decision}
            onChange={(val) => setDecision((val as "approve" | "reject") ?? "approve")}
            required
          />
          <Textarea
            label="Decision Justification & Authorization Signature"
            placeholder="Enter review findings and verification reference..."
            value={comments}
            onChange={(e) => setComments(e.target.value)}
            required
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={onClose}>Cancel</Button>
            <Button
              type="submit"
              color={decision === "approve" ? "red" : "gray"}
              loading={authMutation.isPending}
            >
              Confirm Decision ({decision.toUpperCase()})
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
