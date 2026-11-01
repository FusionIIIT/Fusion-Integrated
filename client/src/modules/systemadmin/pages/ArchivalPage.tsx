import { useState } from "react";
import {
  Stack,
  Table,
  Badge,
  Text,
  Button,
  Paper,
  Loader,
  Alert,
  Tabs,
  Tooltip,
} from "@mantine/core";
import {
  FaArchive,
  FaUndo,
  FaTrashAlt,
  FaCheckCircle,
  FaClock,
} from "react-icons/fa";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useArchivedUsers,
  useArchivedHistoricalData,
  usePurgeRequests,
} from "../api/hooks";
import type {
  ArchivedUserItem,
  ArchivedHistoricalDataItem,
  PermanentPurgeRequestItem,
} from "../api/types";
import {
  ArchiveUserModal,
  RestoreUserModal,
  ArchiveDataModal,
  RestoreDataModal,
  PurgeRequestModal,
  PurgeAuthorizeModal,
} from "../components/ArchivalModals";

export default function ArchivalPage() {
  const [activeTab, setActiveTab] = useState<string | null>("users");

  // Data queries
  const { data: usersData, isLoading: loadingUsers, error: errorUsers } = useArchivedUsers();
  const { data: dataData, isLoading: loadingData, error: errorData } = useArchivedHistoricalData();
  const { data: purgeData, isLoading: loadingPurge, error: errorPurge } = usePurgeRequests();

  // Modal states
  const [archiveUserOpen, setArchiveUserOpen] = useState(false);
  const [restoreUserTarget, setRestoreUserTarget] = useState<ArchivedUserItem | null>(null);

  const [archiveDataOpen, setArchiveDataOpen] = useState(false);
  const [restoreDataTarget, setRestoreDataTarget] = useState<ArchivedHistoricalDataItem | null>(null);

  const [purgeRequestOpen, setPurgeRequestOpen] = useState(false);
  const [purgeAuthTarget, setPurgeAuthTarget] = useState<PermanentPurgeRequestItem | null>(null);

  return (
    <Stack gap="lg">
      <PageHeader
        title="Data & User Archival Management"
        subtitle="Reversible user snapshots, statutory data retention, and dual-authorization permanent purge workflows"
        action={
          activeTab === "users" ? (
            <Button
              leftSection={<FaArchive size={14} />}
              color="orange"
              onClick={() => setArchiveUserOpen(true)}
            >
              Archive User
            </Button>
          ) : activeTab === "historical" ? (
            <Button
              leftSection={<FaArchive size={14} />}
              onClick={() => setArchiveDataOpen(true)}
            >
              Archive Historical Batch
            </Button>
          ) : (
            <Button
              leftSection={<FaTrashAlt size={14} />}
              color="red"
              onClick={() => setPurgeRequestOpen(true)}
            >
              Request Purge
            </Button>
          )
        }
      />

      <Tabs value={activeTab} onChange={setActiveTab}>
        <Tabs.List>
          <Tabs.Tab value="users" leftSection={<FaArchive size={14} />}>
            Archived Users ({usersData?.count ?? 0})
          </Tabs.Tab>
          <Tabs.Tab value="historical" leftSection={<FaClock size={14} />}>
            Historical Data Batches ({dataData?.count ?? 0})
          </Tabs.Tab>
          <Tabs.Tab value="purge" leftSection={<FaTrashAlt size={14} />}>
            Permanent Purge Workflows ({purgeData?.count ?? 0})
          </Tabs.Tab>
        </Tabs.List>

        {/* -------------------- TAB 1: ARCHIVED USERS -------------------- */}
        <Tabs.Panel value="users" pt="md">
          {loadingUsers && (
            <Stack align="center" justify="center" p="xl">
              <Loader />
              <Text c="dimmed">Loading archived users...</Text>
            </Stack>
          )}

          {errorUsers && (
            <Alert color="red" title="Error">
              Failed to load archived users.
            </Alert>
          )}

          {usersData && (
            <Paper withBorder radius="md">
              <Table verticalSpacing="sm" striped highlightOnHover>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Institute ID</Table.Th>
                    <Table.Th>User / Email</Table.Th>
                    <Table.Th>Archived Date</Table.Th>
                    <Table.Th>Reversibility Deadline</Table.Th>
                    <Table.Th>Retention Option</Table.Th>
                    <Table.Th>Status</Table.Th>
                    <Table.Th style={{ width: 120, textAlign: "center" }}>Actions</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {usersData.results.map((u) => {
                    const isReversible =
                      u.status === "reversible" &&
                      new Date(u.reversibility_deadline) > new Date();

                    return (
                      <Table.Tr key={u.id}>
                        <Table.Td>
                          <Text fw={600}>{u.user_details?.institute_id ?? `User #${u.user}`}</Text>
                        </Table.Td>
                        <Table.Td>
                          <Text fw={500}>{u.user_details?.full_name ?? `User #${u.user}`}</Text>
                          <Text size="xs" c="dimmed">{u.user_details?.institute_email ?? "—"}</Text>
                        </Table.Td>
                        <Table.Td>
                          <Text size="sm">{new Date(u.archived_at).toLocaleDateString()}</Text>
                        </Table.Td>
                        <Table.Td>
                          <Text size="sm" c={isReversible ? "blue" : "dimmed"}>
                            {new Date(u.reversibility_deadline).toLocaleDateString()}
                          </Text>
                          {isReversible ? (
                            <Badge size="xs" color="blue" variant="light">Window Open</Badge>
                          ) : (
                            <Badge size="xs" color="gray" variant="light">Window Closed</Badge>
                          )}
                        </Table.Td>
                        <Table.Td>
                          <Text size="sm">{u.retention_option}</Text>
                        </Table.Td>
                        <Table.Td>
                          {u.status === "reversible" ? (
                            <Badge color="green">Reversible</Badge>
                          ) : u.status === "restored" ? (
                            <Badge color="blue">Restored</Badge>
                          ) : (
                            <Badge color="gray">Permanent Non-Restorable</Badge>
                          )}
                        </Table.Td>
                        <Table.Td style={{ textAlign: "center" }}>
                          {isReversible ? (
                            <Button
                              size="xs"
                              variant="light"
                              color="blue"
                              leftSection={<FaUndo size={11} />}
                              onClick={() => setRestoreUserTarget(u)}
                            >
                              Restore
                            </Button>
                          ) : (
                            <Tooltip label="Restoration window expired or user permanently archived (BR-SA-005)">
                              <Text size="xs" c="dimmed">—</Text>
                            </Tooltip>
                          )}
                        </Table.Td>
                      </Table.Tr>
                    );
                  })}
                  {usersData.results.length === 0 && (
                    <Table.Tr>
                      <Table.Td colSpan={7} style={{ textAlign: "center", padding: "2rem" }}>
                        <Text c="dimmed">No archived users recorded.</Text>
                      </Table.Td>
                    </Table.Tr>
                  )}
                </Table.Tbody>
              </Table>
            </Paper>
          )}
        </Tabs.Panel>

        {/* -------------------- TAB 2: HISTORICAL DATA -------------------- */}
        <Tabs.Panel value="historical" pt="md">
          {loadingData && (
            <Stack align="center" justify="center" p="xl">
              <Loader />
              <Text c="dimmed">Loading historical archives...</Text>
            </Stack>
          )}

          {errorData && (
            <Alert color="red" title="Error">
              Failed to load historical data batches.
            </Alert>
          )}

          {dataData && (
            <Paper withBorder radius="md">
              <Table verticalSpacing="sm" striped highlightOnHover>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Category</Table.Th>
                    <Table.Th>Date Span Covered</Table.Th>
                    <Table.Th>Records / Size</Table.Th>
                    <Table.Th>Backup Reference</Table.Th>
                    <Table.Th>Retention Expiry</Table.Th>
                    <Table.Th>Status</Table.Th>
                    <Table.Th style={{ width: 120, textAlign: "center" }}>Actions</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {dataData.results.map((b) => (
                    <Table.Tr key={b.id}>
                      <Table.Td>
                        <Badge variant="outline" color="indigo">{b.category}</Badge>
                      </Table.Td>
                      <Table.Td>
                        <Text size="sm">{b.date_range_start} → {b.date_range_end}</Text>
                      </Table.Td>
                      <Table.Td>
                        <Text fw={500}>{b.record_count.toLocaleString()} records</Text>
                        <Text size="xs" c="dimmed">{(b.storage_size_kb / 1024).toFixed(2)} MB</Text>
                      </Table.Td>
                      <Table.Td>
                        <Text size="xs" ff="monospace">{b.backup_reference}</Text>
                      </Table.Td>
                      <Table.Td>
                        <Text size="sm">{b.retention_expiry_date}</Text>
                      </Table.Td>
                      <Table.Td>
                        {b.status === "archived" ? (
                          <Badge color="green">Active Archive</Badge>
                        ) : b.status === "restored" ? (
                          <Badge color="blue">Restored</Badge>
                        ) : (
                          <Badge color="red">Purged</Badge>
                        )}
                      </Table.Td>
                      <Table.Td style={{ textAlign: "center" }}>
                        {b.status === "archived" ? (
                          <Button
                            size="xs"
                            variant="light"
                            leftSection={<FaUndo size={11} />}
                            onClick={() => setRestoreDataTarget(b)}
                          >
                            Restore
                          </Button>
                        ) : (
                          <Text size="xs" c="dimmed">{b.status}</Text>
                        )}
                      </Table.Td>
                    </Table.Tr>
                  ))}
                  {dataData.results.length === 0 && (
                    <Table.Tr>
                      <Table.Td colSpan={7} style={{ textAlign: "center", padding: "2rem" }}>
                        <Text c="dimmed">No historical data batches archived.</Text>
                      </Table.Td>
                    </Table.Tr>
                  )}
                </Table.Tbody>
              </Table>
            </Paper>
          )}
        </Tabs.Panel>

        {/* -------------------- TAB 3: PERMANENT PURGE -------------------- */}
        <Tabs.Panel value="purge" pt="md">
          {loadingPurge && (
            <Stack align="center" justify="center" p="xl">
              <Loader />
              <Text c="dimmed">Loading purge requests...</Text>
            </Stack>
          )}

          {errorPurge && (
            <Alert color="red" title="Error">
              Failed to load purge requests.
            </Alert>
          )}

          {purgeData && (
            <Paper withBorder radius="md">
              <Table verticalSpacing="sm" striped highlightOnHover>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Request ID / Target</Table.Th>
                    <Table.Th>Target Type</Table.Th>
                    <Table.Th>Requested By (Super Admin)</Table.Th>
                    <Table.Th>Regulatory Authorization</Table.Th>
                    <Table.Th>Status</Table.Th>
                    <Table.Th>IT Head Authorization</Table.Th>
                    <Table.Th style={{ width: 140, textAlign: "center" }}>Dual-Auth Action</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {purgeData.results.map((p) => (
                    <Table.Tr key={p.id}>
                      <Table.Td>
                        <Text fw={600}>Purge #{p.id}</Text>
                        <Text size="xs" c="dimmed">{p.target_summary}</Text>
                      </Table.Td>
                      <Table.Td>
                        <Badge color={p.target_type === "historical_data" ? "violet" : "orange"}>
                          {p.target_type === "historical_data" ? "Historical Data" : "Archived User"}
                        </Badge>
                      </Table.Td>
                      <Table.Td>
                        <Text fw={500}>{p.requested_by}</Text>
                        <Text size="xs" c="dimmed">{new Date(p.requested_at).toLocaleDateString()}</Text>
                      </Table.Td>
                      <Table.Td>
                        <Text size="sm">{p.regulatory_authorization_ref}</Text>
                        <Text size="xs" c="dimmed">{p.request_reason}</Text>
                      </Table.Td>
                      <Table.Td>
                        {p.status === "pending_it_head" ? (
                          <Badge color="orange">Pending IT Head</Badge>
                        ) : p.status === "approved" ? (
                          <Badge color="red">Purged & Completed</Badge>
                        ) : (
                          <Badge color="gray">Rejected</Badge>
                        )}
                      </Table.Td>
                      <Table.Td>
                        {p.it_head_decided_by ? (
                          <div>
                            <Text size="xs" fw={500}>{p.it_head_decided_by}</Text>
                            <Text size="xs" c="dimmed">
                              {p.it_head_decided_at ? new Date(p.it_head_decided_at).toLocaleDateString() : ""}
                            </Text>
                          </div>
                        ) : (
                          <Text size="xs" c="dimmed">Awaiting Review</Text>
                        )}
                      </Table.Td>
                      <Table.Td style={{ textAlign: "center" }}>
                        {p.status === "pending_it_head" ? (
                          <Button
                            size="xs"
                            color="grape"
                            leftSection={<FaCheckCircle size={11} />}
                            onClick={() => setPurgeAuthTarget(p)}
                          >
                            Authorize
                          </Button>
                        ) : (
                          <Text size="xs" c="dimmed">—</Text>
                        )}
                      </Table.Td>
                    </Table.Tr>
                  ))}
                  {purgeData.results.length === 0 && (
                    <Table.Tr>
                      <Table.Td colSpan={7} style={{ textAlign: "center", padding: "2rem" }}>
                        <Text c="dimmed">No purge requests recorded.</Text>
                      </Table.Td>
                    </Table.Tr>
                  )}
                </Table.Tbody>
              </Table>
            </Paper>
          )}
        </Tabs.Panel>
      </Tabs>

      {/* Modals */}
      <ArchiveUserModal
        opened={archiveUserOpen}
        onClose={() => setArchiveUserOpen(false)}
      />

      {restoreUserTarget && (
        <RestoreUserModal
          userId={restoreUserTarget.user}
          instituteId={restoreUserTarget.user_details?.institute_id ?? String(restoreUserTarget.user)}
          opened={Boolean(restoreUserTarget)}
          onClose={() => setRestoreUserTarget(null)}
        />
      )}

      <ArchiveDataModal
        opened={archiveDataOpen}
        onClose={() => setArchiveDataOpen(false)}
      />

      {restoreDataTarget && (
        <RestoreDataModal
          batch={restoreDataTarget}
          opened={Boolean(restoreDataTarget)}
          onClose={() => setRestoreDataTarget(null)}
        />
      )}

      <PurgeRequestModal
        opened={purgeRequestOpen}
        onClose={() => setPurgeRequestOpen(false)}
      />

      {purgeAuthTarget && (
        <PurgeAuthorizeModal
          request={purgeAuthTarget}
          opened={Boolean(purgeAuthTarget)}
          onClose={() => setPurgeAuthTarget(null)}
        />
      )}
    </Stack>
  );
}
