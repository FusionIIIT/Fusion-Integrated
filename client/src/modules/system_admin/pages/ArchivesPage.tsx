import { useEffect, useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  Stack,
  Table,
  Tabs,
  Text,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaArchive, FaPlus, FaUndo } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { PageHeader } from "../../../ui/components/PageHeader";
import { adminApi } from "../api/client";
import type {
  ArchivedUserRecord,
  HistoricalDatasetArchive,
  PermanentPurgeRequest,
} from "../api/types";

export default function ArchivesPage() {
  const { can } = useAuth();
  const canManage = can("system_admin.archive.manage");

  const [activeTab, setActiveTab] = useState<string | null>("users");
  const [archivedUsers, setArchivedUsers] = useState<ArchivedUserRecord[]>([]);
  const [datasets, setDatasets] = useState<HistoricalDatasetArchive[]>([]);
  const [purges, setPurges] = useState<PermanentPurgeRequest[]>([]);

  // Archive User Modal
  const [archiveModalOpen, setArchiveModalOpen] = useState(false);
  const [archiveUserId, setArchiveUserId] = useState("");
  const [archiveReason, setArchiveReason] = useState("");

  // Restore Modal
  const [restoreModalOpen, setRestoreModalOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<ArchivedUserRecord | null>(null);
  const [restoreReason, setRestoreReason] = useState("");

  // Request Purge Modal
  const [purgeModalOpen, setPurgeModalOpen] = useState(false);
  const [purgeDatasetId, setPurgeDatasetId] = useState("");
  const [retentionYears, setRetentionYears] = useState("7.5");
  const [purgeReason, setPurgeReason] = useState("");

  // Authorize Purge Modal
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [selectedPurge, setSelectedPurge] = useState<PermanentPurgeRequest | null>(null);
  const [authRemarks, setAuthRemarks] = useState("");

  const fetchData = () => {
    Promise.all([
      adminApi.getArchivedUsers(),
      adminApi.getDatasets(),
      adminApi.getPurgeRequests(),
    ])
      .then(([usersRes, dsRes, purgeRes]) => {
        setArchivedUsers(usersRes.results);
        setDatasets(dsRes);
        setPurges(purgeRes);
      })
      .catch((err) => {
        notifications.show({ color: "red", message: "Failed to load archives: " + String(err) });
      });
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleArchiveSubmit = async () => {
    try {
      await adminApi.archiveUser(parseInt(archiveUserId, 10), archiveReason);
      notifications.show({ color: "green", message: `User ${archiveUserId} archived successfully.` });
      setArchiveModalOpen(false);
      fetchData();
    } catch (err: unknown) {
      notifications.show({ color: "red", message: "Archival failed: " + String(err) });
    }
  };

  const handleRestoreSubmit = async () => {
    if (!selectedUser) return;
    try {
      await adminApi.restoreUser(selectedUser.user_id, restoreReason);
      notifications.show({ color: "green", message: `User ${selectedUser.username} restored to active system.` });
      setRestoreModalOpen(false);
      fetchData();
    } catch (err: unknown) {
      notifications.show({ color: "red", message: "Restoration failed: " + String(err) });
    }
  };

  const handlePurgeRequestSubmit = async () => {
    try {
      await adminApi.requestPurge(purgeDatasetId, parseFloat(retentionYears), purgeReason);
      notifications.show({ color: "green", message: "Purge request submitted for IT Head dual authorization." });
      setPurgeModalOpen(false);
      fetchData();
    } catch (err: unknown) {
      notifications.show({ color: "red", message: "Purge request failed: " + String(err) });
    }
  };

  const handleDualAuthDecision = async (approve: boolean) => {
    if (!selectedPurge) return;
    try {
      await adminApi.authorizePurge(selectedPurge.id, approve, authRemarks);
      notifications.show({
        color: approve ? "green" : "orange",
        message: `Purge request ${approve ? "approved and executed" : "rejected"}.`,
      });
      setAuthModalOpen(false);
      fetchData();
    } catch (err: unknown) {
      notifications.show({ color: "red", message: "Authorization decision failed: " + String(err) });
    }
  };

  return (
    <Container size="xl" py="lg">
      <PageHeader
        title="Archival Control & Permanent Purge"
        subtitle="Manage cold user records, historical dataset archives, reversible restoration windows, and dual-auth purge decisions."
      />

      <Card withBorder mb="lg" padding="md">
        <Group justify="space-between">
          <Text fw={600} size="lg">
            Archival Operations
          </Text>
          {canManage && (
            <Group gap="sm">
              <Button variant="light" leftSection={<FaArchive />} onClick={() => setArchiveModalOpen(true)}>
                Archive Deactivated User
              </Button>
              <Button color="red" leftSection={<FaPlus />} onClick={() => setPurgeModalOpen(true)}>
                Request Permanent Purge
              </Button>
            </Group>
          )}
        </Group>
      </Card>

      <Tabs value={activeTab} onChange={setActiveTab}>
        <Tabs.List mb="md">
          <Tabs.Tab value="users">Archived Users ({archivedUsers.length})</Tabs.Tab>
          <Tabs.Tab value="datasets">Historical Datasets ({datasets.length})</Tabs.Tab>
          <Tabs.Tab value="purges">Dual-Auth Purge Requests ({purges.length})</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="users">
          <Card withBorder padding="md">
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Institute ID</Table.Th>
                  <Table.Th>Username</Table.Th>
                  <Table.Th>User Type</Table.Th>
                  <Table.Th>Archived Date</Table.Th>
                  <Table.Th>Reversible Until</Table.Th>
                  <Table.Th>Retention Option</Table.Th>
                  <Table.Th>Actions</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {archivedUsers.map((u) => {
                  const reversible = new Date(u.reversible_until) > new Date() && !u.is_permanent;
                  return (
                    <Table.Tr key={u.user_id}>
                      <Table.Td fw={500}>{u.institute_id}</Table.Td>
                      <Table.Td>{u.username}</Table.Td>
                      <Table.Td>{u.user_type}</Table.Td>
                      <Table.Td>{new Date(u.archived_at).toLocaleDateString()}</Table.Td>
                      <Table.Td>
                        {reversible ? (
                          <Badge color="green">Reversible until {new Date(u.reversible_until).toLocaleDateString()}</Badge>
                        ) : (
                          <Badge color="gray">Window Expired</Badge>
                        )}
                      </Table.Td>
                      <Table.Td>{u.retention_option}</Table.Td>
                      <Table.Td>
                        {canManage && reversible && (
                          <Button
                            size="xs"
                            variant="light"
                            color="green"
                            leftSection={<FaUndo size={12} />}
                            onClick={() => {
                              setSelectedUser(u);
                              setRestoreReason("");
                              setRestoreModalOpen(true);
                            }}
                          >
                            Restore Account
                          </Button>
                        )}
                      </Table.Td>
                    </Table.Tr>
                  );
                })}
              </Table.Tbody>
            </Table>
          </Card>
        </Tabs.Panel>

        <Tabs.Panel value="datasets">
          <Card withBorder padding="md">
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Category</Table.Th>
                  <Table.Th>Description</Table.Th>
                  <Table.Th>Date Range</Table.Th>
                  <Table.Th>Record Count</Table.Th>
                  <Table.Th>Backup Reference</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {datasets.map((d) => (
                  <Table.Tr key={d.id}>
                    <Table.Td fw={500}>{d.category}</Table.Td>
                    <Table.Td>{d.description}</Table.Td>
                    <Table.Td>
                      {d.date_range_start} to {d.date_range_end}
                    </Table.Td>
                    <Table.Td>{d.record_count}</Table.Td>
                    <Table.Td style={{ fontFamily: "monospace", fontSize: "0.85rem" }}>
                      {d.backup_reference}
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Card>
        </Tabs.Panel>

        <Tabs.Panel value="purges">
          <Card withBorder padding="md">
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Dataset Identifier</Table.Th>
                  <Table.Th>Requested By (User ID)</Table.Th>
                  <Table.Th>Requested At</Table.Th>
                  <Table.Th>Reason</Table.Th>
                  <Table.Th>Dual Auth Status</Table.Th>
                  <Table.Th>Decision</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {purges.map((p) => (
                  <Table.Tr key={p.id}>
                    <Table.Td fw={500}>{p.dataset_identifier}</Table.Td>
                    <Table.Td>{p.requested_by}</Table.Td>
                    <Table.Td>{new Date(p.requested_at).toLocaleDateString()}</Table.Td>
                    <Table.Td>{p.reason}</Table.Td>
                    <Table.Td>
                      <Badge
                        color={
                          p.status === "purged"
                            ? "red"
                            : p.status === "pending_it_head"
                            ? "orange"
                            : "gray"
                        }
                      >
                        {p.status}
                      </Badge>
                    </Table.Td>
                    <Table.Td>
                      {canManage && p.status === "pending_it_head" && (
                        <Button
                          size="xs"
                          variant="filled"
                          color="indigo"
                          onClick={() => {
                            setSelectedPurge(p);
                            setAuthRemarks("");
                            setAuthModalOpen(true);
                          }}
                        >
                          Dual-Auth Review
                        </Button>
                      )}
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Card>
        </Tabs.Panel>
      </Tabs>

      {/* Archive User Modal */}
      <Modal opened={archiveModalOpen} onClose={() => setArchiveModalOpen(false)} title="Archive Deactivated User">
        <Stack gap="sm">
          <TextInput
            label="User ID"
            required
            placeholder="e.g. 5001"
            value={archiveUserId}
            onChange={(e) => setArchiveUserId(e.currentTarget.value)}
          />
          <TextInput
            label="Reason for Archival"
            required
            placeholder="e.g. Completed degree, records retained per 7-year policy"
            value={archiveReason}
            onChange={(e) => setArchiveReason(e.currentTarget.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setArchiveModalOpen(false)}>
              Cancel
            </Button>
            <Button color="grape" onClick={handleArchiveSubmit}>
              Archive User
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Restore User Modal */}
      <Modal opened={restoreModalOpen} onClose={() => setRestoreModalOpen(false)} title="Restore Archived User">
        <Stack gap="sm">
          <Text size="sm">
            Restore account for <b>{selectedUser?.username}</b> ({selectedUser?.institute_id}) back into the active database?
          </Text>
          <TextInput
            label="Restoration Justification"
            required
            placeholder="e.g. Re-enrolled into PhD program"
            value={restoreReason}
            onChange={(e) => setRestoreReason(e.currentTarget.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setRestoreModalOpen(false)}>
              Cancel
            </Button>
            <Button color="green" onClick={handleRestoreSubmit}>
              Confirm Restoration
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Request Purge Modal */}
      <Modal opened={purgeModalOpen} onClose={() => setPurgeModalOpen(false)} title="Request Permanent Purge">
        <Stack gap="sm">
          <Text size="xs" c="dimmed">
            Requires minimum 7 years elapsed retention. Permanent purge cannot be undone and requires dual authorization by IT Head.
          </Text>
          <TextInput
            label="Dataset Identifier"
            required
            placeholder="e.g. academic_batch_2015"
            value={purgeDatasetId}
            onChange={(e) => setPurgeDatasetId(e.currentTarget.value)}
          />
          <TextInput
            label="Retention Elapsed (Years)"
            required
            type="number"
            step="0.5"
            value={retentionYears}
            onChange={(e) => setRetentionYears(e.currentTarget.value)}
          />
          <TextInput
            label="Purge Reason & Compliance Note"
            required
            placeholder="e.g. 7-year statutory retention cycle complete"
            value={purgeReason}
            onChange={(e) => setPurgeReason(e.currentTarget.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setPurgeModalOpen(false)}>
              Cancel
            </Button>
            <Button color="red" onClick={handlePurgeRequestSubmit}>
              Submit Purge Request
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Dual Authorization Modal */}
      <Modal opened={authModalOpen} onClose={() => setAuthModalOpen(false)} title="IT Head Dual-Authorization Decision">
        <Stack gap="sm">
          <Text size="sm">
            Dataset: <b>{selectedPurge?.dataset_identifier}</b>
          </Text>
          <Text size="sm">
            Requested by: User ID <b>{selectedPurge?.requested_by}</b>
          </Text>
          <TextInput
            label="Authorization Remarks"
            placeholder="e.g. Verified compliance records and approved deletion"
            value={authRemarks}
            onChange={(e) => setAuthRemarks(e.currentTarget.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button color="gray" variant="default" onClick={() => handleDualAuthDecision(false)}>
              Reject Purge
            </Button>
            <Button color="red" onClick={() => handleDualAuthDecision(true)}>
              Approve Permanent Purge
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
