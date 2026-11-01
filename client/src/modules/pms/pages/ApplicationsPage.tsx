import { useState } from "react";
import {
  ActionIcon,
  Button,
  Card,
  Container,
  Drawer,
  Group,
  Menu,
  Paper,
  Select,
  Stack,
  Tabs,
  Text,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  FaCloudUploadAlt,
  FaEllipsisV,
  FaEye,
  FaFileAlt,
  FaHistory,
  FaPlus,
  FaSearch,
  FaTimes,
} from "react-icons/fa";
import { useNavigate } from "react-router-dom";

import { errorMessage } from "../../../lib/http";
import { type Column, DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  downloadDocument,
  useApplication,
  useApplications,
  useWithdrawApplication,
} from "../api/hooks";
import type { PatentApplicationListItem } from "../api/types";
import { DocumentUploadModal } from "../components/DocumentUploadModal";
import { HistoryDrawer } from "../components/HistoryDrawer";
import { StatusBadge } from "../components/StatusBadge";

export default function ApplicationsPage() {
  const navigate = useNavigate();
  const [status, setStatus] = useState<string | null>(null);
  const [search, setSearch] = useState<string>("");
  const [historyAppId, setHistoryAppId] = useState<number | null>(null);
  const [uploadAppId, setUploadAppId] = useState<number | null>(null);
  const [selectedAppId, setSelectedAppId] = useState<number | null>(null);

  const { data, isPending, error } = useApplications({
    status: status || undefined,
    search: search || undefined,
  });

  const { data: detailData, isPending: detailPending } = useApplication(selectedAppId ?? undefined);
  const withdrawMutation = useWithdrawApplication(selectedAppId ?? 0);

  const handleWithdraw = async () => {
    if (!confirm("Are you sure you want to withdraw this patent application? (BR-PMS-008)")) return;
    try {
      await withdrawMutation.mutateAsync({ reason: "Applicant voluntary withdrawal" });
      notifications.show({ color: "green", message: "Application withdrawn." });
    } catch (err) {
      notifications.show({ color: "red", message: errorMessage(err) });
    }
  };

  const columns: Column<PatentApplicationListItem>[] = [
    {
      key: "application_no",
      header: "Application No.",
      render: (row) => (
        <Text fw={600} size="sm">
          {row.application_no}
        </Text>
      ),
    },
    {
      key: "title",
      header: "Invention Title",
      render: (row) => (
        <Stack gap={2}>
          <Text fw={500} size="sm" lineClamp={1}>
            {row.title}
          </Text>
          <Text size="xs" c="dimmed">
            Domain: {row.domain} | Inventor: {row.primary_inventor_name || "N/A"}
          </Text>
        </Stack>
      ),
    },
    {
      key: "status",
      header: "Prosecution Status",
      render: (row) => <StatusBadge status={row.status} />,
    },
    {
      key: "budget_status",
      header: "Budget",
      render: (row) => (
        <Text size="xs" c={row.has_budget ? "teal" : "dimmed"}>
          {row.budget_status.toUpperCase()}
        </Text>
      ),
    },
    {
      key: "submitted_at",
      header: "Submitted",
      render: (row) => (
        <Text size="xs">
          {row.submitted_at ? new Date(row.submitted_at).toLocaleDateString() : "Draft"}
        </Text>
      ),
    },
    {
      key: "actions",
      header: "",
      render: (row) => (
        <Group justify="flex-end" gap="xs">
          <ActionIcon
            variant="subtle"
            color="blue"
            title="View Details"
            onClick={() => setSelectedAppId(row.id)}
          >
            <FaEye />
          </ActionIcon>
          <ActionIcon
            variant="subtle"
            color="gray"
            title="Audit History"
            onClick={() => setHistoryAppId(row.id)}
          >
            <FaHistory />
          </ActionIcon>
          <Menu position="bottom-end">
            <Menu.Target>
              <ActionIcon variant="subtle" color="gray">
                <FaEllipsisV />
              </ActionIcon>
            </Menu.Target>
            <Menu.Dropdown>
              <Menu.Item
                leftSection={<FaCloudUploadAlt />}
                onClick={() => setUploadAppId(row.id)}
              >
                Upload Document
              </Menu.Item>
              {["draft", "submitted", "revisions_requested"].includes(row.status) && (
                <Menu.Item
                  color="red"
                  leftSection={<FaTimes />}
                  onClick={() => {
                    setSelectedAppId(row.id);
                    handleWithdraw();
                  }}
                >
                  Withdraw Application
                </Menu.Item>
              )}
            </Menu.Dropdown>
          </Menu>
        </Group>
      ),
    },
  ];

  return (
    <Container size="xl" py="lg">
      <PageHeader
        title="Patent Applications"
        subtitle="Comprehensive patent portfolio management, internal prosecution, and statutory lifecycle tracking."
        action={
          <Button
            leftSection={<FaPlus />}
            color="blue"
            onClick={() => navigate("/pms/submit")}
          >
            New Patent Submission
          </Button>
        }
      />

      <Paper p="md" mb="md" withBorder>
        <Group justify="space-between">
          <Group>
            <TextInput
              placeholder="Search title, application no..."
              leftSection={<FaSearch />}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{ width: 280 }}
            />
            <Select
              placeholder="All Statuses"
              clearable
              value={status}
              onChange={setStatus}
              data={[
                { value: "draft", label: "Draft" },
                { value: "submitted", label: "Submitted" },
                { value: "under_review", label: "Under Director Review" },
                { value: "revisions_requested", label: "Revisions Requested" },
                { value: "approved", label: "Approved by Director" },
                { value: "attorney_assigned", label: "Attorney Assigned" },
                { value: "filed", label: "Officially Filed" },
                { value: "office_action_received", label: "Office Action Received" },
                { value: "granted", label: "Patent Granted" },
                { value: "withdrawn", label: "Withdrawn" },
              ]}
              style={{ width: 220 }}
            />
          </Group>
        </Group>
      </Paper>

      {error && <ErrorState error={error} />}

      <Card withBorder p={0}>
        <DataTable
          columns={columns}
          rows={data?.results ?? []}
          loading={isPending}
          rowKey={(row) => row.id}
          empty={{
            title: "No patent applications found",
            description: "Submit a new patent disclosure or change filter criteria.",
          }}
        />
      </Card>

      {/* Details Drawer */}
      <Drawer
        opened={selectedAppId != null}
        onClose={() => setSelectedAppId(null)}
        position="right"
        size="xl"
        title={
          <Group>
            <Text fw={700}>Patent Application Details</Text>
            {detailData && <StatusBadge status={detailData.status} />}
          </Group>
        }
      >
        {detailPending && <Text size="sm" c="dimmed">Loading patent specification…</Text>}
        {detailData && (
          <Tabs defaultValue="specification">
            <Tabs.List mb="md">
              <Tabs.Tab value="specification">Specification</Tabs.Tab>
              <Tabs.Tab value="inventors">Inventors ({detailData.inventors?.length ?? 0})</Tabs.Tab>
              <Tabs.Tab value="documents">Documents ({detailData.documents?.length ?? 0})</Tabs.Tab>
              <Tabs.Tab value="prosecution">Prosecution & Filing</Tabs.Tab>
            </Tabs.List>

            <Tabs.Panel value="specification">
              <Stack gap="md">
                <div>
                  <Text fw={600} size="sm">Application Number</Text>
                  <Text size="sm">{detailData.application_no}</Text>
                </div>
                <div>
                  <Text fw={600} size="sm">Title</Text>
                  <Text size="sm">{detailData.title}</Text>
                </div>
                <div>
                  <Text fw={600} size="sm">Abstract</Text>
                  <Paper withBorder p="sm" bg="gray.0">
                    <Text size="sm">{detailData.abstract}</Text>
                  </Paper>
                </div>
                <div>
                  <Text fw={600} size="sm">Detailed Description</Text>
                  <Paper withBorder p="sm" bg="gray.0" mah={250} style={{ overflowY: "auto" }}>
                    <Text size="sm" style={{ whiteSpace: "pre-line" }}>{detailData.description}</Text>
                  </Paper>
                </div>
                <div>
                  <Text fw={600} size="sm">Patent Claims</Text>
                  <Paper withBorder p="sm" bg="gray.0" mah={250} style={{ overflowY: "auto" }}>
                    <Text size="sm" style={{ whiteSpace: "pre-line" }}>{detailData.claims}</Text>
                  </Paper>
                </div>
              </Stack>
            </Tabs.Panel>

            <Tabs.Panel value="inventors">
              <Stack gap="sm">
                {detailData.inventors?.map((inv) => (
                  <Paper key={inv.id} withBorder p="sm">
                    <Group justify="space-between">
                      <div>
                        <Group gap="xs">
                          <Text fw={600} size="sm">{inv.name}</Text>
                          {inv.is_lead && <Text size="xs" c="blue" fw={700}>[LEAD]</Text>}
                        </Group>
                        <Text size="xs" c="dimmed">{inv.email} - {inv.department}</Text>
                      </div>
                      <Group>
                        <Text size="sm" fw={600}>{inv.share_percentage}% share</Text>
                        <StatusBadge status={inv.consent_status} />
                      </Group>
                    </Group>
                  </Paper>
                ))}
              </Stack>
            </Tabs.Panel>

            <Tabs.Panel value="documents">
              <Stack gap="sm">
                <Button
                  leftSection={<FaCloudUploadAlt />}
                  size="xs"
                  variant="light"
                  onClick={() => setUploadAppId(detailData.id)}
                >
                  Upload New Document
                </Button>
                {detailData.documents?.map((doc) => (
                  <Paper key={doc.id} withBorder p="sm">
                    <Group justify="space-between">
                      <div>
                        <Text fw={600} size="sm">{doc.title}</Text>
                        <Text size="xs" c="dimmed">
                          {doc.document_type} (v{doc.version}) | {(doc.file_size / 1024).toFixed(1)} KB
                        </Text>
                      </div>
                      <Button
                        size="xs"
                        variant="subtle"
                        leftSection={<FaFileAlt />}
                        onClick={() => downloadDocument(doc.id, doc.title)}
                      >
                        Download
                      </Button>
                    </Group>
                  </Paper>
                ))}
              </Stack>
            </Tabs.Panel>

            <Tabs.Panel value="prosecution">
              <Stack gap="md">
                {detailData.filing_record ? (
                  <Paper withBorder p="sm" bg="blue.0">
                    <Text fw={700} size="sm">Official Patent Filing Record</Text>
                    <Text size="sm">Filing No: {detailData.filing_record.filing_number}</Text>
                    <Text size="sm">Jurisdiction: {detailData.filing_record.jurisdiction} ({detailData.filing_record.patent_office})</Text>
                    <Text size="sm">Filing Date: {detailData.filing_record.filing_date}</Text>
                  </Paper>
                ) : (
                  <Text size="sm" c="dimmed">No official patent office filing recorded yet.</Text>
                )}

                {detailData.budget && (
                  <Paper withBorder p="sm">
                    <Text fw={700} size="sm">Prosecution Budget</Text>
                    <Text size="sm">Total: ₹ {detailData.budget.total_cost} ({detailData.budget.status.toUpperCase()})</Text>
                    <Text size="xs" c="dimmed">
                      Filing: ₹ {detailData.budget.filing_fees} | Attorney: ₹ {detailData.budget.attorney_fees}
                    </Text>
                  </Paper>
                )}

                {detailData.post_grant && (
                  <Paper withBorder p="sm" bg="teal.0">
                    <Text fw={700} size="sm">Granted Patent Record</Text>
                    <Text size="sm">Patent No: {detailData.post_grant.patent_number}</Text>
                    <Text size="sm">Grant Date: {detailData.post_grant.grant_date}</Text>
                    <Text size="sm">Expiry Date: {detailData.post_grant.expiry_date} (20 Years Term)</Text>
                  </Paper>
                )}
              </Stack>
            </Tabs.Panel>
          </Tabs>
        )}
      </Drawer>

      {/* History Drawer */}
      <HistoryDrawer
        applicationId={historyAppId}
        onClose={() => setHistoryAppId(null)}
      />

      {/* Upload Document Modal */}
      <DocumentUploadModal
        applicationId={uploadAppId}
        opened={uploadAppId != null}
        onClose={() => setUploadAppId(null)}
      />
    </Container>
  );
}
