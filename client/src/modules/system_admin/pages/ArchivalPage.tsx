import { useState } from "react";
import {
  ActionIcon,
  Badge,
  Button,
  Card,
  Grid,
  Group,
  Modal,
  NumberInput,
  Select,
  Stack,
  Table,
  Tabs,
  Text,
  TextInput,
  Textarea,
  Tooltip,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import {
  FaArchive,
  FaCheck,
  FaDatabase,
  FaExclamationTriangle,
  FaHistory,
  FaPlus,
  FaTimes,
  FaTrashAlt,
  FaUndo,
} from "react-icons/fa";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import {
  useArchivedRecords,
  useArchivedUsers,
  useArchiveHistoricalData,
  useArchiveUser,
  useAuthorizePurge,
  useBasicUsers,
  usePurgeRequests,
  useRequestPurge,
  useRestoreHistoricalData,
  useRestoreUser,
} from "../api/hooks";
import type { ArchivedRecord, BasicUser, PurgeRequest } from "../api/types";

export default function ArchivalPage() {
  const { data: archivedRecords = [] } = useArchivedRecords();
  const { data: archivedUsers = [] } = useArchivedUsers();
  const { data: deactivatedUsers = [] } = useBasicUsers({ status: "deactivated" });
  const { data: purgeRequests = [] } = usePurgeRequests();

  const archiveUserMutation = useArchiveUser();
  const restoreUserMutation = useRestoreUser();
  const archiveHistoricalMutation = useArchiveHistoricalData();
  const restoreHistoricalMutation = useRestoreHistoricalData();
  const requestPurgeMutation = useRequestPurge();
  const authorizePurgeMutation = useAuthorizePurge();

  // Archive User Modal
  const [archiveTargetUser, setArchiveTargetUser] = useState<BasicUser | null>(null);
  const [archiveReason, setArchiveReason] = useState("");
  const [retentionYears, setRetentionYears] = useState<number | "">(7);
  const [reversibleDays, setReversibleDays] = useState<number | "">(180);

  // Restore User Modal
  const [restoreTargetUser, setRestoreTargetUser] = useState<BasicUser | null>(null);
  const [restoreReason, setRestoreReason] = useState("");

  // Archive Historical Data Modal
  const [archiveHistOpened, { open: openArchiveHist, close: closeArchiveHist }] = useDisclosure(false);
  const [histCategory, setHistCategory] = useState("placement");
  const [histIdentifier, setHistIdentifier] = useState("");
  const [histPayload, setHistPayload] = useState("{}");
  const [histBackupRef, setHistBackupRef] = useState("");
  const [histRetentionYears, setHistRetentionYears] = useState<number | "">(7);
  const [histReason, setHistReason] = useState("");

  // Restore Historical Data Modal
  const [restoreRecord, setRestoreRecord] = useState<ArchivedRecord | null>(null);
  const [restoreHistReason, setRestoreHistReason] = useState("");

  // Request Purge Modal
  const [purgeRecord, setPurgeRecord] = useState<ArchivedRecord | null>(null);
  const [purgeReason, setPurgeReason] = useState("");

  // IT Head Purge Authorization Modal
  const [authorizeTarget, setAuthorizeTarget] = useState<PurgeRequest | null>(null);
  const [decision, setDecision] = useState<"approved" | "rejected">("approved");
  const [rejectionReason, setRejectionReason] = useState("");

  const handleArchiveUser = async () => {
    if (!archiveTargetUser || !archiveReason) return;
    try {
      await archiveUserMutation.mutateAsync({
        userId: archiveTargetUser.user_id,
        reason: archiveReason,
        retention_years: typeof retentionYears === "number" ? retentionYears : 7,
        reversible_window_days: typeof reversibleDays === "number" ? reversibleDays : 180,
      });
      setArchiveTargetUser(null);
      setArchiveReason("");
    } catch {
      // Handled
    }
  };

  const handleRestoreUser = async () => {
    if (!restoreTargetUser || !restoreReason) return;
    try {
      await restoreUserMutation.mutateAsync({
        userId: restoreTargetUser.user_id,
        reason: restoreReason,
      });
      setRestoreTargetUser(null);
      setRestoreReason("");
    } catch {
      // Handled
    }
  };

  const handleArchiveHistorical = async () => {
    if (!histCategory || !histIdentifier || !histBackupRef) return;
    try {
      const parsed = JSON.parse(histPayload || "{}");
      await archiveHistoricalMutation.mutateAsync({
        category: histCategory,
        identifier: histIdentifier,
        data_payload: parsed,
        retention_years: typeof histRetentionYears === "number" ? histRetentionYears : 7,
        backup_reference: histBackupRef,
        reason: histReason,
      });
      closeArchiveHist();
      setHistIdentifier("");
      setHistBackupRef("");
      setHistReason("");
    } catch {
      // Handled
    }
  };

  const handleRestoreHistorical = async () => {
    if (!restoreRecord || !restoreHistReason) return;
    try {
      await restoreHistoricalMutation.mutateAsync({
        archiveId: restoreRecord.id,
        reason: restoreHistReason,
      });
      setRestoreRecord(null);
      setRestoreHistReason("");
    } catch {
      // Handled
    }
  };

  const handleRequestPurge = async () => {
    if (!purgeRecord || !purgeReason) return;
    try {
      await requestPurgeMutation.mutateAsync({
        archive_id: purgeRecord.id,
        reason: purgeReason,
      });
      setPurgeRecord(null);
      setPurgeReason("");
    } catch {
      // Handled
    }
  };

  const handleAuthorizePurge = async () => {
    if (!authorizeTarget) return;
    try {
      await authorizePurgeMutation.mutateAsync({
        requestId: authorizeTarget.id,
        decision,
        rejection_reason: decision === "rejected" ? rejectionReason : "",
      });
      setAuthorizeTarget(null);
      setRejectionReason("");
    } catch {
      // Handled
    }
  };

  return (
    <Stack gap="lg">
      <PageHeader
        title="Archival & Purge Control Plane"
        subtitle="Historical retention management, reversibility enforcement, and dual-authorized purge (CFR-SA-011..016)"
        action={
          <Button leftSection={<FaDatabase />} onClick={openArchiveHist} color="orange">
            Archive Historical Dataset
          </Button>
        }
      />

      <Tabs defaultValue="users">
        <Tabs.List>
          <Tabs.Tab value="users" leftSection={<FaArchive size={14} />}>
            Archived Users ({archivedUsers.length})
          </Tabs.Tab>
          <Tabs.Tab value="records" leftSection={<FaDatabase size={14} />}>
            Historical System Datasets ({archivedRecords.length})
          </Tabs.Tab>
          <Tabs.Tab value="purge" leftSection={<FaTrashAlt size={14} />}>
            Data Purge Dual Authorization ({purgeRequests.length})
          </Tabs.Tab>
        </Tabs.List>

        {/* Users Tab */}
        <Tabs.Panel value="users" pt="md">
          <Stack gap="md">
            {deactivatedUsers.length > 0 && (
              <Card withBorder p="md" radius="md">
                <Text fw={600} mb="xs">
                  Deactivated Users Ready for Archival ({deactivatedUsers.length})
                </Text>
                <Text size="sm" c="dimmed" mb="md">
                  Only deactivated accounts may be transitioned to the archival repository (BR-SA-004).
                </Text>
                <Table highlightOnHover>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Institute ID</Table.Th>
                      <Table.Th>Name</Table.Th>
                      <Table.Th>Deactivated Since</Table.Th>
                      <Table.Th>Action</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {deactivatedUsers.map((u) => (
                      <Table.Tr key={u.user_id}>
                        <Table.Td>{u.institute_id}</Table.Td>
                        <Table.Td>
                          {u.first_name} {u.last_name}
                        </Table.Td>
                        <Table.Td>{u.deactivated_at ? new Date(u.deactivated_at).toLocaleDateString() : "—"}</Table.Td>
                        <Table.Td>
                          <Button
                            size="xs"
                            color="orange"
                            variant="light"
                            onClick={() => {
                              setArchiveTargetUser(u);
                              setArchiveReason("");
                            }}
                          >
                            Archive User
                          </Button>
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              </Card>
            )}

            <Card withBorder p="md" radius="md">
              <Text fw={600} mb="xs">
                Archived User Records (Read-Only Repository)
              </Text>
              <Table highlightOnHover>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Institute ID</Table.Th>
                    <Table.Th>Name</Table.Th>
                    <Table.Th>Archived On</Table.Th>
                    <Table.Th>Reversibility Window</Table.Th>
                    <Table.Th>Permanence</Table.Th>
                    <Table.Th style={{ textAlign: "right" }}>Actions</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {archivedUsers.length === 0 ? (
                    <Table.Tr>
                      <Table.Td colSpan={6} style={{ textAlign: "center", padding: "30px 0" }}>
                        <Text c="dimmed">No users in archival storage.</Text>
                      </Table.Td>
                    </Table.Tr>
                  ) : (
                    archivedUsers.map((u) => {
                      const isExpired = u.reversible_until && new Date(u.reversible_until) < new Date();
                      const canRestore = !u.is_permanently_archived && !isExpired;

                      return (
                        <Table.Tr key={u.user_id}>
                          <Table.Td fw={600}>{u.institute_id}</Table.Td>
                          <Table.Td>
                            {u.first_name} {u.last_name}
                          </Table.Td>
                          <Table.Td>
                            {u.archived_at ? new Date(u.archived_at).toLocaleDateString() : "—"}
                          </Table.Td>
                          <Table.Td>
                            <Text size="xs">
                              Until {u.reversible_until ? new Date(u.reversible_until).toLocaleDateString() : "—"}
                            </Text>
                          </Table.Td>
                          <Table.Td>
                            {u.is_permanently_archived || isExpired ? (
                              <Badge color="red" size="sm">
                                Non-Restorable
                              </Badge>
                            ) : (
                              <Badge color="green" size="sm">
                                Reversible
                              </Badge>
                            )}
                          </Table.Td>
                          <Table.Td style={{ textAlign: "right" }}>
                            {canRestore && (
                              <Button
                                size="xs"
                                color="teal"
                                variant="outline"
                                leftSection={<FaUndo size={12} />}
                                onClick={() => {
                                  setRestoreTargetUser(u);
                                  setRestoreReason("");
                                }}
                              >
                                Restore User
                              </Button>
                            )}
                          </Table.Td>
                        </Table.Tr>
                      );
                    })
                  )}
                </Table.Tbody>
              </Table>
            </Card>
          </Stack>
        </Tabs.Panel>

        {/* Historical Records Tab */}
        <Tabs.Panel value="records" pt="md">
          <Card withBorder p="md" radius="md">
            <Table highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Category</Table.Th>
                  <Table.Th>Identifier</Table.Th>
                  <Table.Th>Retention Until</Table.Th>
                  <Table.Th>Backup Ref</Table.Th>
                  <Table.Th>Status</Table.Th>
                  <Table.Th style={{ textAlign: "right" }}>Actions</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {archivedRecords.length === 0 ? (
                  <Table.Tr>
                    <Table.Td colSpan={6} style={{ textAlign: "center", padding: "30px 0" }}>
                      <Text c="dimmed">No historical records in archive storage.</Text>
                    </Table.Td>
                  </Table.Tr>
                ) : (
                  archivedRecords.map((r) => {
                    const todayStr = new Date().toISOString().split("T")[0];
                    const retentionElapsed = r.retention_until <= todayStr;

                    return (
                      <Table.Tr key={r.id}>
                        <Table.Td>
                          <Badge variant="dot" size="sm">
                            {r.category}
                          </Badge>
                        </Table.Td>
                        <Table.Td fw={600}>{r.identifier}</Table.Td>
                        <Table.Td>{r.retention_until}</Table.Td>
                        <Table.Td>
                          <Text size="xs" c="dimmed">
                            {r.backup_reference}
                          </Text>
                        </Table.Td>
                        <Table.Td>
                          <StatusBadge status={r.status} />
                        </Table.Td>
                        <Table.Td style={{ textAlign: "right" }}>
                          <Group gap="xs" justify="flex-end">
                            {r.status === "archived" && (
                              <Button
                                size="xs"
                                variant="subtle"
                                color="blue"
                                onClick={() => {
                                  setRestoreRecord(r);
                                  setRestoreHistReason("");
                                }}
                              >
                                Restore
                              </Button>
                            )}
                            {retentionElapsed && r.status === "archived" && (
                              <Button
                                size="xs"
                                color="red"
                                variant="light"
                                onClick={() => {
                                  setPurgeRecord(r);
                                  setPurgeReason("");
                                }}
                              >
                                Request Purge
                              </Button>
                            )}
                          </Group>
                        </Table.Td>
                      </Table.Tr>
                    );
                  })
                )}
              </Table.Tbody>
            </Table>
          </Card>
        </Tabs.Panel>

        {/* Data Purge Tab */}
        <Tabs.Panel value="purge" pt="md">
          <Card withBorder p="md" radius="md">
            <Text size="sm" c="dimmed" mb="md">
              Permanent purge workflow requiring dual authorization: Super Admin submission and IT Head approval (BR-SA-021, BR-SA-022, CW-SA-01).
            </Text>
            <Table highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Request #</Table.Th>
                  <Table.Th>Target Archive</Table.Th>
                  <Table.Th>Submitted By</Table.Th>
                  <Table.Th>Reason</Table.Th>
                  <Table.Th>Status</Table.Th>
                  <Table.Th style={{ textAlign: "right" }}>Dual Authorization</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {purgeRequests.length === 0 ? (
                  <Table.Tr>
                    <Table.Td colSpan={6} style={{ textAlign: "center", padding: "30px 0" }}>
                      <Text c="dimmed">No purge requests submitted.</Text>
                    </Table.Td>
                  </Table.Tr>
                ) : (
                  purgeRequests.map((p) => (
                    <Table.Tr key={p.id}>
                      <Table.Td fw={600}>#{p.id}</Table.Td>
                      <Table.Td>
                        Archive #{p.archived_record?.id} ({p.archived_record?.category}:{p.archived_record?.identifier})
                      </Table.Td>
                      <Table.Td>Admin #{p.requested_by_user_id}</Table.Td>
                      <Table.Td>
                        <Text size="xs" c="dimmed" lineClamp={2}>
                          {p.reason}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        <StatusBadge status={p.status} />
                      </Table.Td>
                      <Table.Td style={{ textAlign: "right" }}>
                        {p.status === "pending_it_head" && (
                          <Button
                            size="xs"
                            color="indigo"
                            onClick={() => {
                              setAuthorizeTarget(p);
                              setDecision("approved");
                              setRejectionReason("");
                            }}
                          >
                            Review & Decide
                          </Button>
                        )}
                      </Table.Td>
                    </Table.Tr>
                  ))
                )}
              </Table.Tbody>
            </Table>
          </Card>
        </Tabs.Panel>
      </Tabs>

      {/* Archive User Modal */}
      <Modal
        opened={!!archiveTargetUser}
        onClose={() => setArchiveTargetUser(null)}
        title="Archive User Account"
        size="md"
      >
        {archiveTargetUser && (
          <Stack gap="sm">
            <Text size="sm">
              Archiving <strong>{archiveTargetUser.first_name} {archiveTargetUser.last_name} ({archiveTargetUser.institute_id})</strong>.
            </Text>

            <NumberInput
              label="Archival Retention Period (Years)"
              description="Minimum retention before purge eligibility (BR-SA-019)"
              required
              value={retentionYears}
              onChange={setRetentionYears}
              min={1}
              max={25}
            />

            <NumberInput
              label="Reversibility Window (Days)"
              description="Window during which the account may be restored to active status (BR-SA-005)"
              required
              value={reversibleDays}
              onChange={setReversibleDays}
              min={30}
              max={365}
            />

            <Textarea
              label="Archival Reason"
              description="Mandatory compliance justification (BR-SA-025)"
              required
              value={archiveReason}
              onChange={(e) => setArchiveReason(e.currentTarget.value)}
            />

            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => setArchiveTargetUser(null)}>
                Cancel
              </Button>
              <Button
                color="orange"
                onClick={handleArchiveUser}
                loading={archiveUserMutation.isPending}
                disabled={!archiveReason}
              >
                Confirm Archival
              </Button>
            </Group>
          </Stack>
        )}
      </Modal>

      {/* Restore User Modal */}
      <Modal
        opened={!!restoreTargetUser}
        onClose={() => setRestoreTargetUser(null)}
        title="Restore Archived User"
        size="md"
      >
        {restoreTargetUser && (
          <Stack gap="sm">
            <Text size="sm">
              Restoring account <strong>{restoreTargetUser.first_name} {restoreTargetUser.last_name} ({restoreTargetUser.institute_id})</strong> to Active status.
            </Text>

            <Textarea
              label="Restoration Rationale"
              required
              value={restoreReason}
              onChange={(e) => setRestoreReason(e.currentTarget.value)}
            />

            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => setRestoreTargetUser(null)}>
                Cancel
              </Button>
              <Button
                color="teal"
                onClick={handleRestoreUser}
                loading={restoreUserMutation.isPending}
                disabled={!restoreReason}
              >
                Restore Account
              </Button>
            </Group>
          </Stack>
        )}
      </Modal>

      {/* Archive Historical Data Modal */}
      <Modal opened={archiveHistOpened} onClose={closeArchiveHist} title="Archive Historical Dataset" size="lg">
        <Stack gap="sm">
          <Select
            label="Module / Category"
            required
            data={["placement", "academic", "hostel", "system_admin"]}
            value={histCategory}
            onChange={(v) => setHistCategory(v || "placement")}
          />

          <TextInput
            label="Dataset Identifier"
            placeholder="e.g. 2023-24_placement_applications"
            required
            value={histIdentifier}
            onChange={(e) => setHistIdentifier(e.currentTarget.value)}
          />

          <TextInput
            label="Pre-Archive Backup Reference"
            description="Verified backup artifact reference prior to table extraction (BR-SA-018)"
            placeholder="e.g. pg_dump_fusion_20261101_bk01"
            required
            value={histBackupRef}
            onChange={(e) => setHistBackupRef(e.currentTarget.value)}
          />

          <NumberInput
            label="Retention Period (Years)"
            required
            value={histRetentionYears}
            onChange={setHistRetentionYears}
            min={1}
            max={25}
          />

          <Textarea
            label="Data Payload (JSON)"
            minRows={5}
            value={histPayload}
            onChange={(e) => setHistPayload(e.currentTarget.value)}
            style={{ fontFamily: "monospace" }}
          />

          <Textarea
            label="Reason"
            value={histReason}
            onChange={(e) => setHistReason(e.currentTarget.value)}
          />

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={closeArchiveHist}>
              Cancel
            </Button>
            <Button
              color="orange"
              onClick={handleArchiveHistorical}
              loading={archiveHistoricalMutation.isPending}
              disabled={!histIdentifier || !histBackupRef}
            >
              Archive Dataset
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Request Purge Modal */}
      <Modal opened={!!purgeRecord} onClose={() => setPurgeRecord(null)} title="Request Permanent Data Purge" size="md">
        {purgeRecord && (
          <Stack gap="sm">
            <Alert color="red" icon={<FaExclamationTriangle />}>
              Permanent purge cannot be undone. Requires dual authorization by IT Head before execution (BR-SA-021, BR-SA-022).
            </Alert>

            <Text size="sm">
              Target: <strong>{purgeRecord.category}:{purgeRecord.identifier}</strong>
              <br />
              Retention expired on: {purgeRecord.retention_until}
            </Text>

            <Textarea
              label="Purge Justification"
              required
              value={purgeReason}
              onChange={(e) => setPurgeReason(e.currentTarget.value)}
            />

            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => setPurgeRecord(null)}>
                Cancel
              </Button>
              <Button
                color="red"
                onClick={handleRequestPurge}
                loading={requestPurgeMutation.isPending}
                disabled={!purgeReason}
              >
                Submit for IT Head Authorization
              </Button>
            </Group>
          </Stack>
        )}
      </Modal>

      {/* IT Head Purge Authorization Modal */}
      <Modal
        opened={!!authorizeTarget}
        onClose={() => setAuthorizeTarget(null)}
        title="IT Head Dual Authorization Decision"
        size="md"
      >
        {authorizeTarget && (
          <Stack gap="sm">
            <Text size="sm">
              Request #{authorizeTarget.id} submitted by Super Admin.
              <br />
              Justification: <em>{authorizeTarget.reason}</em>
            </Text>

            <Select
              label="Dual Authorization Decision"
              required
              data={[
                { value: "approved", label: "Approve Permanent Purge (BW-SA-01)" },
                { value: "rejected", label: "Reject Purge Request (BW-SA-02)" },
              ]}
              value={decision}
              onChange={(v) => setDecision((v as "approved" | "rejected") || "approved")}
            />

            {decision === "rejected" && (
              <Textarea
                label="Rejection Reason"
                required
                value={rejectionReason}
                onChange={(e) => setRejectionReason(e.currentTarget.value)}
              />
            )}

            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => setAuthorizeTarget(null)}>
                Cancel
              </Button>
              <Button
                color={decision === "approved" ? "red" : "gray"}
                onClick={handleAuthorizePurge}
                loading={authorizePurgeMutation.isPending}
                disabled={decision === "rejected" && !rejectionReason}
              >
                Record Decision
              </Button>
            </Group>
          </Stack>
        )}
      </Modal>
    </Stack>
  );
}
