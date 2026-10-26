import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Checkbox,
  Container,
  Divider,
  Group,
  Modal,
  NumberInput,
  Select,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  Textarea,
} from "@mantine/core";
import { DateInput } from "@mantine/dates";
import { notifications } from "@mantine/notifications";
import {
  FaCalendarCheck,
  FaCalendarPlus,
  FaFileInvoice,
  FaPrint,
  FaUndo,
  FaUserFriends,
} from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import {
  useApplications,
  useApply,
  useCancel,
  usePrintable,
  useRenominateSubstitute,
  useSubmitResumption,
  useWithdraw,
} from "../api/hooks";
import {
  CATEGORY_LABELS,
  STATUS_LABELS,
  type LeaveApplication,
} from "../api/types";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";

const CATEGORY_OPTIONS = Object.entries(CATEGORY_LABELS).map(([v, l]) => ({
  value: v,
  label: l,
}));

const HALF_OPTIONS = [
  { value: "full", label: "Full Day" },
  { value: "first_half", label: "First Half (Morning)" },
  { value: "second_half", label: "Second Half (Afternoon)" },
];

export default function MyLeavePage() {
  const { data, isPending, error } = useApplications();
  const apply = useApply();
  const withdraw = useWithdraw();
  const cancel = useCancel();
  const resume = useSubmitResumption();
  const renominate = useRenominateSubstitute();

  // Apply Modal state
  const [openApply, setOpenApply] = useState(false);
  const [category, setCategory] = useState<string | null>("cl");
  const [start, setStart] = useState<Date | null>(null);
  const [end, setEnd] = useState<Date | null>(null);
  const [half, setHalf] = useState<string | null>("full");
  const [purpose, setPurpose] = useState("");
  const [substituteId, setSubstituteId] = useState<number | string>("");
  const [isStationLeave, setIsStationLeave] = useState(false);
  const [stationStart, setStationStart] = useState<Date | null>(null);
  const [stationEnd, setStationEnd] = useState<Date | null>(null);
  const [stationAddress, setStationAddress] = useState("");
  const [stationContact, setStationContact] = useState("");

  // Action Modals state
  const [cancelModalApp, setCancelModalApp] = useState<LeaveApplication | null>(null);
  const [cancelReason, setCancelReason] = useState("");

  const [resumeModalApp, setResumeModalApp] = useState<LeaveApplication | null>(null);
  const [actualResumeDate, setActualResumeDate] = useState<Date | null>(null);
  const [resumeNote, setResumeNote] = useState("");

  const [renominateModalApp, setRenominateModalApp] = useState<LeaveApplication | null>(null);
  const [newSubstituteId, setNewSubstituteId] = useState<number | string>("");

  const [printAppId, setPrintAppId] = useState<number | null>(null);
  const { data: printableData, isPending: isPrintPending } = usePrintable(printAppId);

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  function handleApply() {
    if (!category || !start || !end) return;

    const payload: Record<string, unknown> = {
      category,
      start_date: start.toISOString().slice(0, 10),
      end_date: end.toISOString().slice(0, 10),
      half: category === "cl" ? (half || "full") : "full",
      purpose,
    };

    if (substituteId && Number(substituteId) > 0) {
      payload.substitute_user_id = Number(substituteId);
    }

    if (isStationLeave) {
      payload.station_leave = {
        station_start: stationStart ? stationStart.toISOString().slice(0, 10) : payload.start_date,
        station_end: stationEnd ? stationEnd.toISOString().slice(0, 10) : payload.end_date,
        address: stationAddress,
        contact: stationContact,
      };
    }

    apply.mutate(payload, {
      onSuccess: () => {
        notifications.show({
          color: "green",
          title: "Leave Submitted",
          message: "Your leave application has been submitted successfully.",
        });
        setOpenApply(false);
        resetApplyForm();
      },
      onError: (e) =>
        notifications.show({
          color: "red",
          title: "Application Failed",
          message: errorMessage(e),
        }),
    });
  }

  function resetApplyForm() {
    setCategory("cl");
    setStart(null);
    setEnd(null);
    setHalf("full");
    setPurpose("");
    setSubstituteId("");
    setIsStationLeave(false);
    setStationStart(null);
    setStationEnd(null);
    setStationAddress("");
    setStationContact("");
  }

  function handleCancelSubmit() {
    if (!cancelModalApp) return;
    cancel.mutate(
      { id: cancelModalApp.id, reason: cancelReason },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Cancellation Requested",
            message: "Cancellation request sent to Sanctioning Authority.",
          });
          setCancelModalApp(null);
          setCancelReason("");
        },
        onError: (e) =>
          notifications.show({
            color: "red",
            title: "Cancellation Request Failed",
            message: errorMessage(e),
          }),
      },
    );
  }

  function handleResumeSubmit() {
    if (!resumeModalApp || !actualResumeDate) return;
    resume.mutate(
      {
        id: resumeModalApp.id,
        actual_resumption_date: actualResumeDate.toISOString().slice(0, 10),
        note: resumeNote,
      },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Duty Resumption Reported",
            message: "Resumption report submitted for review and attendance sync.",
          });
          setResumeModalApp(null);
          setActualResumeDate(null);
          setResumeNote("");
        },
        onError: (e) =>
          notifications.show({
            color: "red",
            title: "Resumption Submission Failed",
            message: errorMessage(e),
          }),
      },
    );
  }

  function handleRenominateSubmit() {
    if (!renominateModalApp || !newSubstituteId) return;
    renominate.mutate(
      { id: renominateModalApp.id, substitute_user_id: Number(newSubstituteId) },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Substitute Re-nominated",
            message: "Nomination request sent to new substitute.",
          });
          setRenominateModalApp(null);
          setNewSubstituteId("");
        },
        onError: (e) =>
          notifications.show({
            color: "red",
            title: "Re-nomination Failed",
            message: errorMessage(e),
          }),
      },
    );
  }

  return (
    <Container size="xl">
      <PageHeader
        title="My Leave"
        subtitle="Your leave applications, status tracking, and service actions"
        action={
          <Button leftSection={<FaCalendarPlus size={14} />} onClick={() => setOpenApply(true)}>
            Apply for leave
          </Button>
        }
      />

      <Card padding="lg">
        <DataTable<LeaveApplication>
          rows={data?.results ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          columns={[
            {
              key: "category",
              header: "Type & ID",
              render: (r) => (
                <Stack gap={2}>
                  <Group gap="xs">
                    <Text fw={600}>{CATEGORY_LABELS[r.category] ?? r.category.toUpperCase()}</Text>
                    {r.is_offline_record && (
                      <Badge size="xs" color="gray" variant="outline">
                        Offline Sync
                      </Badge>
                    )}
                  </Group>
                  <Text size="xs" c="dimmed">
                    Ref #{r.id} {r.half !== "full" ? `(${r.half.replace("_", " ")})` : ""}
                  </Text>
                </Stack>
              ),
            },
            {
              key: "period",
              header: "Period & Days",
              render: (r) => (
                <Stack gap={2}>
                  <Text size="sm">
                    {r.start_date} — {r.end_date}
                  </Text>
                  <Text size="xs" c="dimmed">
                    {r.chargeable_days} chargeable day(s)
                  </Text>
                </Stack>
              ),
            },
            {
              key: "substitute",
              header: "Substitute",
              render: (r) =>
                r.substitute_user_id ? (
                  <Group gap="xs">
                    <Text size="sm">User #{r.substitute_user_id}</Text>
                    <Badge
                      size="xs"
                      color={
                        r.substitute_status === "accepted"
                          ? "green"
                          : r.substitute_status === "declined"
                            ? "red"
                            : "yellow"
                      }
                    >
                      {r.substitute_status}
                    </Badge>
                  </Group>
                ) : (
                  <Text size="xs" c="dimmed">
                    None required
                  </Text>
                ),
            },
            {
              key: "status",
              header: "Workflow Status",
              render: (r) => {
                const label = STATUS_LABELS[r.status] ?? r.status;
                const color =
                  r.status === "approved" || r.status === "resumed"
                    ? "green"
                    : r.status === "rejected" || r.status === "cancelled"
                      ? "red"
                      : r.status === "forwarded"
                        ? "blue"
                        : "yellow";
                return (
                  <Stack gap={2}>
                    <Badge color={color} variant="light">
                      {label}
                    </Badge>
                    {r.status === "forwarded" && r.recommendation_note && (
                      <Text size="xs" c="dimmed">
                        Recommended: {r.recommendation_note}
                      </Text>
                    )}
                    {r.decision_note && (
                      <Text size="xs" c="dimmed">
                        Note: {r.decision_note}
                      </Text>
                    )}
                  </Stack>
                );
              },
            },
            {
              key: "actions",
              header: "Actions",
              align: "right",
              render: (r) => (
                <Group justify="flex-end" gap="xs">
                  {/* Slip Print Button */}
                  <Button
                    size="xs"
                    variant="subtle"
                    color="blue"
                    leftSection={<FaPrint size={12} />}
                    onClick={() => setPrintAppId(r.id)}
                  >
                    Slip
                  </Button>

                  {/* Re-nominate if substitute declined */}
                  {r.substitute_status === "declined" && r.status === "submitted" && (
                    <Button
                      size="xs"
                      variant="light"
                      color="orange"
                      leftSection={<FaUserFriends size={12} />}
                      onClick={() => setRenominateModalApp(r)}
                    >
                      Re-nominate
                    </Button>
                  )}

                  {/* Withdraw if submitted */}
                  {r.status === "submitted" && (
                    <Button
                      size="xs"
                      variant="subtle"
                      color="gray"
                      loading={withdraw.isPending}
                      onClick={() => withdraw.mutate(r.id)}
                    >
                      Withdraw
                    </Button>
                  )}

                  {/* Cancellation request before start date */}
                  {r.status === "approved" && (
                    <Button
                      size="xs"
                      variant="light"
                      color="red"
                      leftSection={<FaUndo size={12} />}
                      onClick={() => setCancelModalApp(r)}
                    >
                      Cancel Leave
                    </Button>
                  )}

                  {/* Duty Resumption reporting */}
                  {r.status === "approved" && ["el", "col", "vl"].includes(r.category) && (
                    <Button
                      size="xs"
                      variant="light"
                      color="teal"
                      leftSection={<FaCalendarCheck size={12} />}
                      onClick={() => {
                        setResumeModalApp(r);
                        setActualResumeDate(new Date(r.end_date));
                      }}
                    >
                      Resume Duty
                    </Button>
                  )}
                </Group>
              ),
            },
          ]}
          empty={{
            icon: FaCalendarPlus,
            title: "No leave applications",
            description: "Submit an application and it will be tracked here.",
          }}
        />
      </Card>

      {/* Apply Leave Modal */}
      <Modal
        opened={openApply}
        onClose={() => setOpenApply(false)}
        title={<Text fw={600}>Apply for Leave</Text>}
        size="lg"
      >
        <Stack gap="md">
          <SimpleGrid cols={2}>
            <Select
              label="Leave Category"
              data={CATEGORY_OPTIONS}
              value={category}
              onChange={setCategory}
              required
            />
            {category === "cl" ? (
              <Select
                label="Day Duration"
                data={HALF_OPTIONS}
                value={half}
                onChange={setHalf}
              />
            ) : (
              <TextInput label="Duration" value="Full Day" disabled />
            )}
          </SimpleGrid>

          <SimpleGrid cols={2}>
            <DateInput
              label="From Date"
              value={start}
              onChange={(d) => {
                setStart(d);
                if (half !== "full" && d) setEnd(d);
              }}
              required
            />
            <DateInput
              label="To Date"
              value={end}
              onChange={setEnd}
              disabled={half !== "full"}
              required
            />
          </SimpleGrid>

          <NumberInput
            label="Nominated Substitute (Colleague User ID)"
            placeholder="e.g. 102"
            value={substituteId}
            onChange={setSubstituteId}
            min={1}
            description="Nominate an institute colleague to take over responsibilities during your absence."
          />

          <Textarea
            label="Purpose of Leave"
            placeholder="State reasons for leave..."
            value={purpose}
            onChange={(e) => setPurpose(e.currentTarget.value)}
            minRows={2}
          />

          <Divider label="Station Leave Permission" labelPosition="center" />

          <Checkbox
            label="Permission required to leave station / headquarters"
            checked={isStationLeave}
            onChange={(e) => setIsStationLeave(e.currentTarget.checked)}
          />

          {isStationLeave && (
            <Stack gap="xs" p="xs" style={{ background: "#f8f9fa", borderRadius: 6 }}>
              <SimpleGrid cols={2}>
                <DateInput
                  label="Leaving Station From"
                  value={stationStart ?? start}
                  onChange={setStationStart}
                />
                <DateInput
                  label="Returning to Station On"
                  value={stationEnd ?? end}
                  onChange={setStationEnd}
                />
              </SimpleGrid>
              <TextInput
                label="Address During Leave"
                placeholder="Full address where reachable..."
                value={stationAddress}
                onChange={(e) => setStationAddress(e.currentTarget.value)}
              />
              <TextInput
                label="Emergency Contact Phone"
                placeholder="+91..."
                value={stationContact}
                onChange={(e) => setStationContact(e.currentTarget.value)}
              />
            </Stack>
          )}

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setOpenApply(false)}>
              Cancel
            </Button>
            <Button onClick={handleApply} loading={apply.isPending}>
              Submit Application
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Cancellation Request Modal */}
      <Modal
        opened={Boolean(cancelModalApp)}
        onClose={() => setCancelModalApp(null)}
        title="Request Leave Cancellation"
      >
        <Stack gap="sm">
          <Text size="sm">
            You are requesting cancellation for approved leave (#{cancelModalApp?.id}) from{" "}
            {cancelModalApp?.start_date} to {cancelModalApp?.end_date}.
          </Text>
          <Textarea
            label="Reason for Cancellation"
            placeholder="Explain why this approved leave is no longer required..."
            value={cancelReason}
            onChange={(e) => setCancelReason(e.currentTarget.value)}
            required
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setCancelModalApp(null)}>
              Dismiss
            </Button>
            <Button color="red" onClick={handleCancelSubmit} loading={cancel.isPending}>
              Submit Cancellation Request
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Duty Resumption Modal */}
      <Modal
        opened={Boolean(resumeModalApp)}
        onClose={() => setResumeModalApp(null)}
        title="Report Return to Duty (Resumption)"
      >
        <Stack gap="sm">
          <Text size="sm">
            Report your return to duty for #{resumeModalApp?.id} ({resumeModalApp?.category.toUpperCase()}).
            The authority will verify this date to adjust attendance records and leave balances.
          </Text>
          <DateInput
            label="Actual Date of Resumption"
            value={actualResumeDate}
            onChange={setActualResumeDate}
            required
          />
          <Textarea
            label="Resumption Note / Remarks"
            placeholder="e.g. Resumed duty on forenoon after journey..."
            value={resumeNote}
            onChange={(e) => setResumeNote(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setResumeModalApp(null)}>
              Dismiss
            </Button>
            <Button color="teal" onClick={handleResumeSubmit} loading={resume.isPending}>
              Submit Resumption Report
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Re-nominate Substitute Modal */}
      <Modal
        opened={Boolean(renominateModalApp)}
        onClose={() => setRenominateModalApp(null)}
        title="Re-nominate Responsibility Substitute"
      >
        <Stack gap="sm">
          <Text size="sm" c="red">
            Your previous substitute declined the nomination. Nominate a replacement colleague to proceed.
          </Text>
          <NumberInput
            label="New Substitute Colleague User ID"
            value={newSubstituteId}
            onChange={setNewSubstituteId}
            min={1}
            required
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setRenominateModalApp(null)}>
              Cancel
            </Button>
            <Button color="orange" onClick={handleRenominateSubmit} loading={renominate.isPending}>
              Confirm Re-nomination
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Printable Slip Preview Modal */}
      <Modal
        opened={Boolean(printAppId)}
        onClose={() => setPrintAppId(null)}
        title="Official Leave Application Slip"
        size="lg"
      >
        {isPrintPending ? (
          <Text>Loading slip...</Text>
        ) : printableData ? (
          <Stack gap="md" p="md" style={{ border: "1px dashed #ced4da", borderRadius: 8 }}>
            <Group justify="space-between" align="flex-start">
              <Stack gap={2}>
                <Text fw={700} size="lg">
                  PDPM IIITDM JABALPUR
                </Text>
                <Text size="sm" c="dimmed">
                  EMPLOYEE LEAVE APPLICATION SLIP
                </Text>
              </Stack>
              <Badge size="lg" color="blue">
                Ref #{printAppId}
              </Badge>
            </Group>

            <Divider />

            <SimpleGrid cols={2}>
              <Text size="sm">
                <strong>Applicant ID:</strong> #{printableData?.application ? (printableData.application as LeaveApplication).user_id : "—"}
              </Text>
              <Text size="sm">
                <strong>Department:</strong> {(printableData?.application as LeaveApplication)?.department || "General"}
              </Text>
              <Text size="sm">
                <strong>Leave Type:</strong> {CATEGORY_LABELS[(printableData?.application as LeaveApplication)?.category] ?? "—"}
              </Text>
              <Text size="sm">
                <strong>Duration:</strong> {(printableData?.application as LeaveApplication)?.start_date} to {(printableData?.application as LeaveApplication)?.end_date}
              </Text>
              <Text size="sm">
                <strong>Chargeable Days:</strong> {(printableData?.application as LeaveApplication)?.chargeable_days}
              </Text>
              <Text size="sm">
                <strong>Current Status:</strong> {(printableData?.application as LeaveApplication)?.status.toUpperCase()}
              </Text>
            </SimpleGrid>

            {(printableData?.application as LeaveApplication)?.station_leave && (
              <Stack gap={4} p="xs" style={{ background: "#f1f3f5", borderRadius: 4 }}>
                <Text size="xs" fw={700}>
                  STATION LEAVE DETAILS:
                </Text>
                <Text size="xs">
                  Address: {(printableData.application as LeaveApplication).station_leave?.address || "—"}
                </Text>
                <Text size="xs">
                  Contact: {(printableData.application as LeaveApplication).station_leave?.contact || "—"}
                </Text>
              </Stack>
            )}

            <Group justify="space-between" mt="md">
              <Text size="xs" c="dimmed">
                Generated at: {String(printableData.generated_at)}
              </Text>
              <Button
                leftSection={<FaFileInvoice size={14} />}
                onClick={() => window.print()}
              >
                Print / Save PDF
              </Button>
            </Group>
          </Stack>
        ) : null}
      </Modal>
    </Container>
  );
}
