import { useEffect, useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  Stack,
  Text,
  TextInput,
  Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useNavigate } from "react-router-dom";
import { errorMessage } from "../../../lib/http";
import { saveBlob } from "../../../lib/download";
import { DataTable } from "../../../ui/components/DataTable";
import { PageHeader } from "../../../ui/components/PageHeader";
import { leaveApi } from "../api/client";
import type { LeaveApplication } from "../api/types";

function getStatusColor(status: string) {
  switch (status) {
    case "approved":
      return "green";
    case "under_review":
    case "substitute_pending":
    case "extension_requested":
      return "blue";
    case "rejected":
    case "cancelled":
      return "red";
    case "withdrawn":
      return "gray";
    case "resumption_submitted":
      return "cyan";
    default:
      return "yellow";
  }
}

function formatLocalDate(date: Date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

export default function MyLeavesPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [apps, setApps] = useState<LeaveApplication[]>([]);

  // Modals for cancel and resume
  const [cancelModalApp, setCancelModalApp] = useState<LeaveApplication | null>(null);
  const [cancelReason, setCancelReason] = useState("");
  const [resumeModalApp, setResumeModalApp] = useState<LeaveApplication | null>(null);
  const [resumptionDate, setResumptionDate] = useState("");
  const [extensionModalApp, setExtensionModalApp] = useState<LeaveApplication | null>(null);
  const [extensionStart, setExtensionStart] = useState("");
  const [extensionEnd, setExtensionEnd] = useState("");
  const [extensionPurpose, setExtensionPurpose] = useState("");
  const [actionLoading, setActionLoading] = useState(false);

  const fetchApplications = async () => {
    try {
      setLoading(true);
      const data = await leaveApi.getMyApplications();
      setApps(data);
    } catch (err) {
      notifications.show({
        title: "Error",
        message: errorMessage(err),
        color: "red",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApplications();
  }, []);

  const handleWithdraw = async (id: number) => {
    if (!window.confirm("Are you sure you want to withdraw this application?")) return;
    try {
      await leaveApi.withdrawApplication(id, "Withdrawn by employee");
      notifications.show({ title: "Withdrawn", message: "Application withdrawn.", color: "gray" });
      fetchApplications();
    } catch (err) {
      notifications.show({ title: "Error", message: errorMessage(err), color: "red" });
    }
  };

  const handleExport = async (id: number) => {
    try {
      saveBlob(await leaveApi.exportApplication(id), `leave-application-${id}.csv`);
    } catch (err) {
      notifications.show({ title: "Export failed", message: errorMessage(err), color: "red" });
    }
  };

  const handlePrint = async (id: number) => {
    try {
      saveBlob(await leaveApi.printApplication(id), `leave-application-${id}.html`);
    } catch (err) {
      notifications.show({ title: "Print view failed", message: errorMessage(err), color: "red" });
    }
  };

  const handleCancelRequest = async () => {
    if (!cancelModalApp || !cancelReason.trim()) return;
    try {
      setActionLoading(true);
      await leaveApi.requestCancellation(cancelModalApp.id, cancelReason);
      notifications.show({ title: "Cancellation Requested", message: "Cancellation request sent for review.", color: "teal" });
      setCancelModalApp(null);
      setCancelReason("");
      fetchApplications();
    } catch (err) {
      notifications.show({ title: "Error", message: errorMessage(err), color: "red" });
    } finally {
      setActionLoading(false);
    }
  };

  const handleResumeSubmit = async () => {
    if (!resumeModalApp || !resumptionDate) return;
    try {
      setActionLoading(true);
      await leaveApi.submitResumption(resumeModalApp.id, resumptionDate);
      notifications.show({ title: "Resumed", message: "Resumption report submitted for review.", color: "teal" });
      setResumeModalApp(null);
      setResumptionDate("");
      fetchApplications();
    } catch (err) {
      notifications.show({ title: "Error", message: errorMessage(err), color: "red" });
    } finally {
      setActionLoading(false);
    }
  };

  const handleExtensionSubmit = async () => {
    if (!extensionModalApp || !extensionStart || !extensionEnd || !extensionPurpose.trim()) return;
    try {
      setActionLoading(true);
      await leaveApi.requestExtension(extensionModalApp.id, {
        start_date: extensionStart, end_date: extensionEnd, purpose: extensionPurpose.trim(),
      });
      notifications.show({ title: "Extension Requested", message: "Your extension request was sent for review.", color: "teal" });
      setExtensionModalApp(null);
      setExtensionPurpose("");
      fetchApplications();
    } catch (err) {
      notifications.show({ title: "Error", message: errorMessage(err), color: "red" });
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <Container size="xl">
      <PageHeader
        title="My Leaves"
        subtitle="Track your leave requests, withdrawal, pre-start cancellation, and resumption of duty."
        action={
          <Button onClick={() => navigate("/leave/apply")}>
            Apply for Leave
          </Button>
        }
      />

      <Card padding="lg" shadow="sm" radius="md" withBorder>
        <DataTable<LeaveApplication>
          rows={apps}
          loading={loading}
          rowKey={(r) => r.id}
          empty={{ title: "No leave applications", description: "You have not submitted any leave applications yet." }}
          columns={[
            { key: "id", header: "ID", render: (r) => `#${r.id}` },
            {
              key: "category",
              header: "Category",
              render: (r) => (
                <Badge variant="light" color="indigo">
                  {r.category} {r.half_day_type !== "full" ? `(${r.half_day_type})` : ""}
                </Badge>
              ),
            },
            { key: "dates", header: "Dates", render: (r) => `${r.start_date} → ${r.end_date}` },
            { key: "days", header: "Days", render: (r) => `${r.days_count} d` },
            { key: "purpose", header: "Purpose", render: (r) => <Text size="sm" lineClamp={1}>{r.purpose}</Text> },
            {
              key: "status",
              header: "Status",
              render: (r) => (
                <Badge color={getStatusColor(r.status)}>
                  {r.status.replace(/_/g, " ").toUpperCase()}
                </Badge>
              ),
            },
            {
              key: "actions",
              header: "Actions",
              render: (r) => (
                <Group gap="xs">
                  <Button size="xs" variant="light" onClick={() => handleExport(r.id)}>Export</Button>
                  <Button size="xs" variant="subtle" onClick={() => handlePrint(r.id)}>Print</Button>
                  {["substitute_pending", "under_review", "extension_requested"].includes(r.status) && (
                    <Button size="xs" variant="subtle" color="red" onClick={() => handleWithdraw(r.id)}>
                      Withdraw
                    </Button>
                  )}
                  {r.status === "approved" && (
                    <>
                      <Button size="xs" variant="outline" color="orange" disabled={apps.some((child) => child.parent_leave_id === r.id && child.status === "cancel_requested")} onClick={() => setCancelModalApp(r)}>
                        {apps.some((child) => child.parent_leave_id === r.id && child.status === "cancel_requested") ? "Cancellation Pending" : "Cancel"}
                      </Button>
                      {!r.resumption_reviewed_at && ["EL", "COL", "VL"].includes(r.category) && (
                        <Button size="xs" variant="outline" color="teal" onClick={() => setResumeModalApp(r)}>
                          Resume
                        </Button>
                      )}
                      {["EL", "COL", "VL"].includes(r.category) &&
                        new Date(r.start_date) <= new Date() && new Date(r.end_date) >= new Date() && (
                          <Button size="xs" variant="outline" onClick={() => {
                            setExtensionModalApp(r);
                            const next = new Date(`${r.end_date}T00:00:00`);
                            next.setDate(next.getDate() + 1);
                            setExtensionStart(formatLocalDate(next));
                          }}>
                            Extend
                          </Button>
                        )}
                    </>
                  )}
                </Group>
              ),
            },
          ]}
        />
      </Card>

      {/* Cancellation Modal */}
      <Modal
        opened={!!cancelModalApp}
        onClose={() => setCancelModalApp(null)}
        title="Request Cancellation of Approved Leave"
      >
        <Stack gap="md">
          <Text size="sm">
            Leave must not have started yet. If approved, your deducted leave balance will be restored.
          </Text>
          <TextInput
            label="Reason for Cancellation"
            placeholder="e.g. Travel postponed"
            value={cancelReason}
            onChange={(e) => setCancelReason(e.currentTarget.value)}
            required
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setCancelModalApp(null)}>Dismiss</Button>
            <Button color="orange" onClick={handleCancelRequest} loading={actionLoading}>
              Submit Cancellation
            </Button>
          </Group>
        </Stack>
      </Modal>

      <Modal opened={!!extensionModalApp} onClose={() => setExtensionModalApp(null)} title="Request Leave Extension">
        <Stack gap="md">
          <Text size="sm">Request additional EL, COL, or VL while your leave is ongoing. Only the added days will be deducted if approved.</Text>
          <TextInput type="date" label="Extension Start" value={extensionStart} readOnly required />
          <TextInput type="date" label="Extension End" value={extensionEnd} onChange={(e) => setExtensionEnd(e.currentTarget.value)} required />
          <Textarea label="Reason" value={extensionPurpose} onChange={(e) => setExtensionPurpose(e.currentTarget.value)} required />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setExtensionModalApp(null)}>Dismiss</Button>
            <Button onClick={handleExtensionSubmit} loading={actionLoading}>Submit Extension</Button>
          </Group>
        </Stack>
      </Modal>

      {/* Resumption Modal */}
      <Modal
        opened={!!resumeModalApp}
        onClose={() => setResumeModalApp(null)}
        title="Declare Resumption of Duty"
      >
        <Stack gap="md">
          <Text size="sm">
            Declare the actual date you resumed duty. Any early or late days will adjust your balance upon review.
          </Text>
          <TextInput
            type="date"
            label="Resumption Date"
            value={resumptionDate}
            onChange={(e) => setResumptionDate(e.currentTarget.value)}
            required
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setResumeModalApp(null)}>Dismiss</Button>
            <Button color="teal" onClick={handleResumeSubmit} loading={actionLoading}>
              Submit Resumption
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
