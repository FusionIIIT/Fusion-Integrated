import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  Badge,
  Button,
  Card,
  Container,
  Group,
  Loader,
  Modal,
  Paper,
  Select,
  Stack,
  Switch,
  Table,
  Text,
  Textarea,
  TextInput,
  Title,
} from "@mantine/core";
import { errorMessage, http } from "../../lib/http";

type View = "apply" | "mine" | "balance" | "approvals" | "admin";
type Item = Record<string, unknown>;
type Submission = { path: string; body: Item };

const TITLES: Record<View, string> = {
  apply: "Apply for Leave",
  mine: "My Leave Applications",
  balance: "My Leave Balances & History",
  approvals: "Assigned Leave Approvals & Tasks",
  admin: "Leave Administration & Sync",
};

const LEAVE_TYPES = [
  { value: "CL", label: "Casual Leave" },
  { value: "RH", label: "Restricted Holiday" },
  { value: "SCL", label: "Special Casual Leave" },
  { value: "EL", label: "Earned Leave" },
  { value: "COL", label: "Commuted Leave" },
  { value: "VL", label: "Vacation Leave" },
];

const formatValue = (val: unknown) =>
  val == null ? "—" : typeof val === "object" ? JSON.stringify(val) : String(val);

function DataTable({
  rows,
  actions,
}: {
  rows: Item[];
  actions?: (item: Item) => React.ReactNode;
}) {
  const first = rows[0];
  if (!first) return <Text c="dimmed" size="sm">No entries yet.</Text>;
  return (
    <Table.ScrollContainer minWidth={650}>
      <Table striped highlightOnHover withTableBorder>
        <Table.Thead>
          <Table.Tr>
            {Object.keys(first).map((k) => (
              <Table.Th key={k}>{k.replaceAll("_", " ")}</Table.Th>
            ))}
            {actions && <Table.Th>Actions</Table.Th>}
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {rows.map((row, index) => (
            <Table.Tr key={formatValue(row.id ?? index)}>
              {Object.keys(first).map((key) => (
                <Table.Td key={key} style={{ overflowWrap: "anywhere" }}>
                  {key === "status" ? (
                    <Badge variant="light" color={String(row[key]).includes("REJECT") ? "red" : String(row[key]).includes("APPROV") ? "green" : "blue"}>
                      {formatValue(row[key])}
                    </Badge>
                  ) : (
                    <Text size="xs">{formatValue(row[key])}</Text>
                  )}
                </Table.Td>
              ))}
              {actions && <Table.Td>{actions(row)}</Table.Td>}
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  );
}

export default function ElmPage({ view }: { view: View }) {
  const queryClient = useQueryClient();
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  
  // Application form fields
  const [category, setCategory] = useState("CL");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [halfDay, setHalfDay] = useState("NONE");
  const [reason, setReason] = useState("");
  const [medicalEvidence, setMedicalEvidence] = useState("");
  const [stationLeave, setStationLeave] = useState(false);
  const [stationLocation, setStationLocation] = useState("");
  const [substituteId, setSubstituteId] = useState("");
  const [remarks, setRemarks] = useState("");

  // Modals & Action dialogs
  const [activeModal, setActiveModal] = useState<"print" | "extend" | "resume" | "replace_sub" | null>(null);
  const [selectedApp, setSelectedApp] = useState<Item | null>(null);
  const [printableData, setPrintableData] = useState<string>("");
  const [extEndDate, setExtEndDate] = useState("");
  const [extReason, setExtReason] = useState("");
  const [extSubId, setExtSubId] = useState("");
  const [resumptionDate, setResumptionDate] = useState("");
  const [resumptionRemarks, setResumptionRemarks] = useState("");
  const [replacementSubId, setReplacementSubId] = useState("");

  // Admin form fields
  const [userId, setUserId] = useState("");
  const [kind, setKind] = useState("staff");
  const [unit, setUnit] = useState("");
  const [designation, setDesignation] = useState("");
  const [headId, setHeadId] = useState("");
  const [establishmentId, setEstablishmentId] = useState("");
  const [authorityId, setAuthorityId] = useState("");
  const [allotted, setAllotted] = useState("");
  const [year, setYear] = useState(String(new Date().getFullYear()));
  const [holidayDate, setHolidayDate] = useState("");
  const [holidayName, setHolidayName] = useState("");
  const [holidayKind, setHolidayKind] = useState("RH");
  const [published, setPublished] = useState(false);

  // Admin offline leave fields
  const [offEmpId, setOffEmpId] = useState("");
  const [offCategory, setOffCategory] = useState("EL");
  const [offStart, setOffStart] = useState("");
  const [offEnd, setOffEnd] = useState("");
  const [offRef, setOffRef] = useState("");
  const [offReason, setOffReason] = useState("");

  const query = useQuery({
    queryKey: ["leave-elm", view],
    retry: false,
    queryFn: async (): Promise<Item> => {
      if (view === "admin") {
        const [profiles, holidays, slas] = await Promise.all([
          http.get("/elm/admin/profiles"),
          http.get("/elm/admin/holidays"),
          http.get("/elm/admin/sla-config"),
        ]);
        return {
          profiles: profiles.data.results,
          holidays: holidays.data.results,
          slas: slas.data.results,
        };
      }
      if (view === "apply") {
        return { types: (await http.get("/elm/types")).data };
      }
      if (view === "balance") {
        const [balResp, txResp] = await Promise.all([
          http.get("/elm/balances"),
          http.get("/elm/transactions"),
        ]);
        return {
          balances: balResp.data.results,
          transactions: txResp.data.results,
        };
      }
      const endpoints: Record<"mine" | "approvals", string> = {
        mine: "/elm/applications",
        approvals: "/elm/approvals",
      };
      return (await http.get<Item>(endpoints[view])).data;
    },
  });

  const mutation = useMutation({
    mutationFn: async ({ path, body }: Submission) =>
      (await http.post(path, body)).data,
    onSuccess: async () => {
      setError("");
      setNotice("Saved successfully.");
      setActiveModal(null);
      await queryClient.invalidateQueries({ queryKey: ["leave-elm"] });
    },
    onError: (err: unknown) => {
      setNotice("");
      setError(errorMessage(err));
    },
  });

  const submitAction = (path: string, body: Item) => {
    setError("");
    setNotice("");
    mutation.mutate({ path, body });
  };

  const results = (key: string): Item[] => {
    const rows = query.data?.[key];
    return Array.isArray(rows) ? (rows as Item[]) : [];
  };

  const openPrintModal = async (item: Item) => {
    try {
      const resp = await http.get<{ printable_text: string }>(`/elm/applications/${item.id}/printable`);
      setPrintableData(resp.data.printable_text);
      setSelectedApp(item);
      setActiveModal("print");
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  const approvalsActions = (item: Item) => {
    const st = String(item.status);
    const cat = String(item.category);

    if (st.includes("SUB")) {
      return (
        <Group gap="xs" wrap="nowrap">
          <Button
            size="xs"
            color="green"
            loading={mutation.isPending}
            onClick={() => submitAction(`/elm/applications/${item.id}/decide`, { action: "accept_substitute", remarks })}
          >
            Accept
          </Button>
          <Button
            size="xs"
            color="red"
            variant="light"
            loading={mutation.isPending}
            onClick={() => submitAction(`/elm/applications/${item.id}/decide`, { action: "decline_substitute", remarks })}
          >
            Decline
          </Button>
        </Group>
      );
    }

    if (st.includes("ESTABLISHMENT")) {
      return (
        <Button
          size="xs"
          color="blue"
          loading={mutation.isPending}
          onClick={() => submitAction(`/elm/applications/${item.id}/decide`, { action: "verify_and_route", remarks })}
        >
          Verify & Route
        </Button>
      );
    }

    if (st === "RESUMPTION_PENDING") {
      return (
        <Button
          size="xs"
          color="indigo"
          loading={mutation.isPending}
          onClick={() => submitAction(`/elm/applications/${item.id}/review-resumption`, { remarks })}
        >
          Review Resumption
        </Button>
      );
    }

    if (st.includes("CANCELLATION")) {
      const isUHFinal = st === "CANCELLATION_PENDING" && ["CL", "RH"].includes(cat);
      const isSanctionFinal = st === "CANCELLATION_SANCTION";
      if (isUHFinal || isSanctionFinal) {
        return (
          <Group gap="xs" wrap="nowrap">
            <Button
              size="xs"
              color="green"
              loading={mutation.isPending}
              onClick={() => submitAction(`/elm/applications/${item.id}/decide`, { action: "approve_cancellation", remarks })}
            >
              Approve Cancellation
            </Button>
            <Button
              size="xs"
              color="red"
              variant="light"
              loading={mutation.isPending}
              onClick={() => submitAction(`/elm/applications/${item.id}/decide`, { action: "reject_cancellation", remarks })}
            >
              Reject Cancellation
            </Button>
          </Group>
        );
      }
      return (
        <Group gap="xs" wrap="nowrap">
          <Button
            size="xs"
            color="teal"
            loading={mutation.isPending}
            onClick={() => submitAction(`/elm/applications/${item.id}/decide`, { action: "recommend_cancellation", remarks })}
          >
            Recommend Cancel
          </Button>
          <Button
            size="xs"
            color="orange"
            variant="light"
            loading={mutation.isPending}
            onClick={() => submitAction(`/elm/applications/${item.id}/decide`, { action: "not_recommend_cancellation", remarks })}
          >
            Not Recommend Cancel
          </Button>
        </Group>
      );
    }

    if (st === "AWAITING_DIRECTOR" || st === "RECOMMENDED" || st === "EXTENSION_SANCTION" || ["CL", "RH"].includes(cat)) {
      return (
        <Group gap="xs" wrap="nowrap">
          <Button
            size="xs"
            color="green"
            loading={mutation.isPending}
            onClick={() => submitAction(`/elm/applications/${item.id}/decide`, { action: "approve", remarks })}
          >
            Approve
          </Button>
          <Button
            size="xs"
            color="red"
            variant="light"
            loading={mutation.isPending}
            onClick={() => submitAction(`/elm/applications/${item.id}/decide`, { action: "reject", remarks })}
          >
            Reject
          </Button>
        </Group>
      );
    }

    return (
      <Group gap="xs" wrap="nowrap">
        <Button
          size="xs"
          color="teal"
          loading={mutation.isPending}
          onClick={() => submitAction(`/elm/applications/${item.id}/decide`, { action: "recommend", remarks })}
        >
          Recommend
        </Button>
        <Button
          size="xs"
          color="orange"
          variant="light"
          loading={mutation.isPending}
          onClick={() => submitAction(`/elm/applications/${item.id}/decide`, { action: "not_recommend", remarks })}
        >
          Not Recommend
        </Button>
      </Group>
    );
  };

  const myApplicationsActions = (item: Item) => {
    const st = String(item.status);
    const cat = String(item.category);
    const isOngoing = ["EL", "COL", "VL"].includes(cat);

    return (
      <Group gap="xs" wrap="nowrap">
        <Button size="xs" variant="default" onClick={() => openPrintModal(item)}>
          Print
        </Button>

        {st === "ACTION_REQUIRED" && (
          <Button
            size="xs"
            color="indigo"
            onClick={() => {
              setSelectedApp(item);
              setActiveModal("replace_sub");
            }}
          >
            Replace Sub
          </Button>
        )}

        {["AWAITING_SUB", "ACTION_REQUIRED", "PENDING", "RECOMMENDED", "AWAITING_DIRECTOR", "AWAITING_ESTABLISHMENT", "EXTENSION_PENDING", "EXTENSION_AWAITING_SUB"].includes(st) && (
          <Button
            size="xs"
            variant="light"
            color="red"
            loading={mutation.isPending}
            onClick={() => submitAction(`/elm/applications/${item.id}/withdraw`, {})}
          >
            Withdraw
          </Button>
        )}

        {st === "APPROVED" && (
          <>
            <Button
              size="xs"
              variant="light"
              color="orange"
              loading={mutation.isPending}
              onClick={() => submitAction(`/elm/applications/${item.id}/cancel`, { remarks: "Request cancellation" })}
            >
              Cancel Leave
            </Button>
            {isOngoing && (
              <>
                <Button
                  size="xs"
                  color="cyan"
                  onClick={() => {
                    setSelectedApp(item);
                    setExtEndDate(String(item.end_date));
                    setActiveModal("extend");
                  }}
                >
                  Extend
                </Button>
                <Button
                  size="xs"
                  color="teal"
                  onClick={() => {
                    setSelectedApp(item);
                    setResumptionDate(String(item.end_date));
                    setActiveModal("resume");
                  }}
                >
                  Resume Duty
                </Button>
              </>
            )}
          </>
        )}
      </Group>
    );
  };

  return (
    <Container size="xl" py="lg">
      <Stack gap="lg">
        <Title order={2}>{TITLES[view]}</Title>
        {error && <Alert color="red">{error}</Alert>}
        {notice && <Alert color="green">{notice}</Alert>}
        {query.isPending && <Loader size="sm" />}
        {query.isError && <Alert color="red">{errorMessage(query.error)}</Alert>}

        {view === "apply" && (
          <Card withBorder>
            <Stack>
              <Select
                label="Leave type"
                data={LEAVE_TYPES}
                value={category}
                onChange={(v) => setCategory(v ?? "CL")}
              />
              <Group grow>
                <TextInput
                  label="Start date"
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.currentTarget.value)}
                />
                <TextInput
                  label="End date"
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.currentTarget.value)}
                />
              </Group>
              {category === "CL" && (
                <Select
                  label="Leave portion"
                  data={[
                    { value: "NONE", label: "Full day" },
                    { value: "FIRST", label: "First half" },
                    { value: "SECOND", label: "Second half" },
                  ]}
                  value={halfDay}
                  onChange={(v) => setHalfDay(v ?? "NONE")}
                />
              )}
              {category === "COL" && (
                <TextInput
                  label="Medical Certificate Reference / Details"
                  value={medicalEvidence}
                  onChange={(e) => setMedicalEvidence(e.currentTarget.value)}
                />
              )}
              <Textarea
                label="Purpose / reason"
                value={reason}
                onChange={(e) => setReason(e.currentTarget.value)}
              />
              <TextInput
                label="Substitute IAM user ID (optional)"
                type="number"
                value={substituteId}
                onChange={(e) => setSubstituteId(e.currentTarget.value)}
              />
              <Switch
                label="Station Leave (outside Jabalpur)"
                checked={stationLeave}
                onChange={(e) => setStationLeave(e.currentTarget.checked)}
              />
              {stationLeave && (
                <TextInput
                  label="Station Leave destination"
                  value={stationLocation}
                  onChange={(e) => setStationLocation(e.currentTarget.value)}
                />
              )}
              <Button
                loading={mutation.isPending}
                onClick={() =>
                  submitAction("/elm/applications", {
                    category,
                    start_date: startDate,
                    end_date: endDate,
                    reason,
                    medical_evidence: medicalEvidence,
                    half_day: category === "CL" ? halfDay : "NONE",
                    station_leave: stationLeave,
                    station_location: stationLocation,
                    substitute_user_id: substituteId ? Number(substituteId) : null,
                  })
                }
              >
                Submit application
              </Button>
            </Stack>
          </Card>
        )}

        {view === "mine" && (
          <DataTable
            rows={results("results")}
            actions={myApplicationsActions}
          />
        )}

        {view === "balance" && (
          <Stack gap="xl">
            <Card withBorder>
              <Title order={4} mb="sm">Current Leave Balances</Title>
              <DataTable rows={results("balances")} />
            </Card>
            <Card withBorder>
              <Title order={4} mb="sm">Leave Account Transactions & Carry Forward History</Title>
              <DataTable rows={results("transactions")} />
            </Card>
          </Stack>
        )}

        {view === "approvals" && (
          <Stack>
            <Textarea
              label="Decision / Review Remarks"
              placeholder="Enter remarks for approval/rejection/recommendation"
              value={remarks}
              onChange={(e) => setRemarks(e.currentTarget.value)}
            />
            <DataTable rows={results("results")} actions={approvalsActions} />
          </Stack>
        )}

        {view === "admin" && (
          <Stack gap="xl">
            <Card withBorder>
              <Stack>
                <Title order={4}>Synchronize Retrospective Offline Sanctioned Leave (BR-EL-029)</Title>
                <Group grow>
                  <TextInput
                    label="Employee IAM User ID"
                    type="number"
                    value={offEmpId}
                    onChange={(e) => setOffEmpId(e.currentTarget.value)}
                  />
                  <Select
                    label="Category"
                    data={LEAVE_TYPES}
                    value={offCategory}
                    onChange={(v) => setOffCategory(v ?? "EL")}
                  />
                </Group>
                <Group grow>
                  <TextInput
                    label="Start date"
                    type="date"
                    value={offStart}
                    onChange={(e) => setOffStart(e.currentTarget.value)}
                  />
                  <TextInput
                    label="End date"
                    type="date"
                    value={offEnd}
                    onChange={(e) => setOffEnd(e.currentTarget.value)}
                  />
                </Group>
                <TextInput
                  label="Sanction Reference Evidence"
                  placeholder="e.g. Order #ESTT/2026/044 signed by Director"
                  value={offRef}
                  onChange={(e) => setOffRef(e.currentTarget.value)}
                />
                <TextInput
                  label="Remarks / Reason"
                  value={offReason}
                  onChange={(e) => setOffReason(e.currentTarget.value)}
                />
                <Button
                  color="teal"
                  loading={mutation.isPending}
                  onClick={() =>
                    submitAction("/elm/admin/offline-leave", {
                      employee_id: Number(offEmpId),
                      category: offCategory,
                      start_date: offStart,
                      end_date: offEnd,
                      sanction_reference: offRef,
                      reason: offReason,
                    })
                  }
                >
                  Record Offline Sanctioned Leave
                </Button>
              </Stack>
            </Card>

            <Card withBorder>
              <Stack>
                <Title order={4}>Scheduled Operations & Event Triggers</Title>
                <Group>
                  <Button
                    color="indigo"
                    loading={mutation.isPending}
                    onClick={() => submitAction("/elm/admin/year-end", { year: Number(year) })}
                  >
                    Execute Year-End Processing ({year})
                  </Button>
                  <Button
                    variant="outline"
                    loading={mutation.isPending}
                    onClick={() => submitAction("/elm/admin/sla-process", {})}
                  >
                    Evaluate Workflow SLA Thresholds
                  </Button>
                </Group>
              </Stack>
            </Card>

            <Card withBorder>
              <Stack>
                <Title order={4}>Employee Profile and Approval Hierarchy Configuration</Title>
                <Group grow>
                  <TextInput
                    label="IAM User ID"
                    type="number"
                    value={userId}
                    onChange={(e) => setUserId(e.currentTarget.value)}
                  />
                  <Select
                    label="Employee category"
                    data={["faculty", "staff"]}
                    value={kind}
                    onChange={(v) => setKind(v ?? "staff")}
                  />
                </Group>
                <Group grow>
                  <TextInput
                    label="Unit / Department"
                    value={unit}
                    onChange={(e) => setUnit(e.currentTarget.value)}
                  />
                  <TextInput
                    label="Designation"
                    value={designation}
                    onChange={(e) => setDesignation(e.currentTarget.value)}
                  />
                </Group>
                <Group grow>
                  <TextInput
                    label="Unit Head IAM User ID"
                    value={headId}
                    onChange={(e) => setHeadId(e.currentTarget.value)}
                  />
                  <TextInput
                    label="Establishment IAM User ID (optional)"
                    value={establishmentId}
                    onChange={(e) => setEstablishmentId(e.currentTarget.value)}
                  />
                  <TextInput
                    label="Higher Sanction IAM User ID"
                    value={authorityId}
                    onChange={(e) => setAuthorityId(e.currentTarget.value)}
                  />
                </Group>
                <Button
                  loading={mutation.isPending}
                  onClick={() =>
                    submitAction("/elm/admin/profiles", {
                      user_id: Number(userId),
                      employee_kind: kind,
                      unit,
                      designation,
                      unit_head_user_id: headId ? Number(headId) : null,
                      establishment_user_id: establishmentId ? Number(establishmentId) : null,
                      sanction_authority_user_id: authorityId ? Number(authorityId) : null,
                    })
                  }
                >
                  Save Employee Hierarchy Profile
                </Button>
                <DataTable rows={results("profiles")} />
              </Stack>
            </Card>

            <Card withBorder>
              <Stack>
                <Title order={4}>Allot Leave Balance</Title>
                <Group grow>
                  <Select
                    label="Leave type"
                    data={LEAVE_TYPES}
                    value={category}
                    onChange={(v) => setCategory(v ?? "CL")}
                  />
                  <TextInput
                    label="Year"
                    type="number"
                    value={year}
                    onChange={(e) => setYear(e.currentTarget.value)}
                  />
                  <TextInput
                    label="Allotted days"
                    type="number"
                    value={allotted}
                    onChange={(e) => setAllotted(e.currentTarget.value)}
                  />
                </Group>
                <Button
                  loading={mutation.isPending}
                  onClick={() =>
                    submitAction("/elm/admin/balances", {
                      employee_id: Number(userId),
                      category,
                      year: Number(year),
                      allotted: Number(allotted),
                    })
                  }
                >
                  Save Allotment
                </Button>
              </Stack>
            </Card>

            <Card withBorder>
              <Stack>
                <Title order={4}>Maintain and Publish Institute Holiday & Vacation Calendar</Title>
                <Group grow>
                  <TextInput
                    label="Date"
                    type="date"
                    value={holidayDate}
                    onChange={(e) => setHolidayDate(e.currentTarget.value)}
                  />
                  <TextInput
                    label="Holiday Name"
                    value={holidayName}
                    onChange={(e) => setHolidayName(e.currentTarget.value)}
                  />
                  <Select
                    label="Kind"
                    data={[
                      { value: "RH", label: "Restricted Holiday" },
                      { value: "CLOSED", label: "Closed Holiday" },
                      { value: "VACATION", label: "Vacation Window" },
                    ]}
                    value={holidayKind}
                    onChange={(v) => setHolidayKind(v ?? "RH")}
                  />
                  <Switch
                    label="Published"
                    checked={published}
                    onChange={(e) => setPublished(e.currentTarget.checked)}
                  />
                </Group>
                <Button
                  loading={mutation.isPending}
                  onClick={() =>
                    submitAction("/elm/admin/holidays", {
                      date: holidayDate,
                      name: holidayName,
                      kind: holidayKind,
                      published,
                    })
                  }
                >
                  Save Calendar Entry
                </Button>
                <DataTable rows={results("holidays")} />
              </Stack>
            </Card>
          </Stack>
        )}

        {/* Modal: Printable representation */}
        <Modal
          opened={activeModal === "print"}
          onClose={() => setActiveModal(null)}
          title="Printable / Exportable Leave Application"
          size="lg"
        >
          <Paper withBorder p="md" bg="gray.0">
            <Text component="pre" style={{ fontFamily: "monospace", whiteSpace: "pre-wrap" }}>
              {printableData}
            </Text>
          </Paper>
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => window.print()}>
              Print Form
            </Button>
            <Button onClick={() => setActiveModal(null)}>Close</Button>
          </Group>
        </Modal>

        {/* Modal: Replacement Substitute */}
        <Modal
          opened={activeModal === "replace_sub"}
          onClose={() => setActiveModal(null)}
          title="Nominate Replacement Substitute"
        >
          <Stack>
            <Text size="sm">
              The previous substitute declined request #{String(selectedApp?.id)}. Please enter a new substitute IAM user ID:
            </Text>
            <TextInput
              label="Replacement Substitute User ID"
              type="number"
              value={replacementSubId}
              onChange={(e) => setReplacementSubId(e.currentTarget.value)}
            />
            <Button
              color="indigo"
              loading={mutation.isPending}
              onClick={() =>
                submitAction(`/elm/applications/${selectedApp?.id}/replace-substitute`, {
                  replacement_substitute_user_id: Number(replacementSubId),
                })
              }
            >
              Assign Replacement Substitute
            </Button>
          </Stack>
        </Modal>

        {/* Modal: Extend Leave */}
        <Modal
          opened={activeModal === "extend"}
          onClose={() => setActiveModal(null)}
          title="Request Leave Extension"
        >
          <Stack>
            <Text size="sm">
              Current Leave Period ends on: {String(selectedApp?.end_date)}
            </Text>
            <TextInput
              label="New Extended End Date"
              type="date"
              value={extEndDate}
              onChange={(e) => setExtEndDate(e.currentTarget.value)}
            />
            <TextInput
              label="Substitute User ID (optional)"
              type="number"
              value={extSubId}
              onChange={(e) => setExtSubId(e.currentTarget.value)}
            />
            <Textarea
              label="Extension Reason"
              value={extReason}
              onChange={(e) => setExtReason(e.currentTarget.value)}
            />
            <Button
              color="cyan"
              loading={mutation.isPending}
              onClick={() =>
                submitAction(`/elm/applications/${selectedApp?.id}/extend`, {
                  end_date: extEndDate,
                  reason: extReason,
                  substitute_user_id: extSubId ? Number(extSubId) : null,
                })
              }
            >
              Submit Extension Request
            </Button>
          </Stack>
        </Modal>

        {/* Modal: Resume Duty */}
        <Modal
          opened={activeModal === "resume"}
          onClose={() => setActiveModal(null)}
          title="Submit Duty Resumption"
        >
          <Stack>
            <Text size="sm">
              Approved Leave Period: {String(selectedApp?.start_date)} to {String(selectedApp?.end_date)}
            </Text>
            <TextInput
              label="Actual Duty Resumption Date"
              type="date"
              value={resumptionDate}
              onChange={(e) => setResumptionDate(e.currentTarget.value)}
            />
            <Textarea
              label="Remarks / Verification Details"
              value={resumptionRemarks}
              onChange={(e) => setResumptionRemarks(e.currentTarget.value)}
            />
            <Button
              color="teal"
              loading={mutation.isPending}
              onClick={() =>
                submitAction(`/elm/applications/${selectedApp?.id}/resume`, {
                  actual_resumption_date: resumptionDate,
                  remarks: resumptionRemarks,
                })
              }
            >
              Submit Resumption of Duty
            </Button>
          </Stack>
        </Modal>
      </Stack>
    </Container>
  );
}
