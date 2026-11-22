import { useEffect, useState, type FormEvent } from "react";
import {
  Alert, Badge, Button, Card, Checkbox, Container, Group, Loader,
  Select, Stack, Table, Text, Textarea, TextInput, Title,
} from "@mantine/core";
import { useLocation } from "react-router-dom";

import { http } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";

type LeaveRequest = {
  id: number;
  category: string;
  start_date: string;
  end_date: string;
  requested_days: string;
  purpose: string;
  status: string;
  request_type: string;
  final_decision?: string;
  current_assignee_user_id?: number | null;
  substitute_user_id?: number | null;
};

type LeavePolicy = {
  id: number;
  category: string;
  annual_entitlement: string;
  employee_scope: "all" | "faculty" | "staff";
  carry_forward: boolean;
  continuous_counting: boolean;
  medical_evidence_required: boolean;
  enabled: boolean;
};

type VacationPeriod = {
  id: number;
  name: string;
  start_date: string;
  end_date: string;
  external_reference: string;
  active: boolean;
};

type LeaveCalendar = {
  id: number;
  name: string;
  year: number;
  status: "draft" | "published";
  published_at?: string | null;
};

type LeaveHierarchy = {
  id: number;
  unit_key: string;
  unit_head_user_id: number | null;
  establishment_user_id: number | null;
  sanctioning_authority_user_id: number | null;
  director_user_id: number | null;
  active: boolean;
};

type ELMNotice = {
  id: number;
  kind: string;
  message: string;
  application_id: number | null;
  created_at: string;
  read_at: string | null;
};

type SLAConfig = {
  reminder_after_hours: number;
  escalation_after_hours: number;
  escalation_user_id: number | null;
};

type EmployeeKind = "faculty" | "staff";

type LeaveBalance = {
  year: number;
  category: string;
  entitlement: string;
  carried_in: string;
  converted_in: string;
  consumed: string;
  lapsed: string;
  converted_out: string;
  available: string;
};

type ListResponse<T> = { results: T[] };
type ReviewDecision = "approve" | "reject" | "recommended" | "not_recommended" | "route" | "review";
type ReviewAction = { decision: ReviewDecision; label: string; color?: string };

function reviewActions(request: LeaveRequest): ReviewAction[] {
  if (request.status === "awaiting_unit_head" || request.status === "awaiting_cancellation_unit_head") {
    if ((request.category === "CL" || request.category === "RH")
      && (request.request_type === "leave" || request.request_type === "offline")) {
      return [{ decision: "approve", label: "Approve" }, { decision: "reject", label: "Reject", color: "red" }];
    }
    return [
      { decision: "recommended", label: "Recommend" },
      { decision: "not_recommended", label: "Not recommended", color: "red" },
    ];
  }
  if (request.status === "awaiting_establishment") return [{ decision: "route", label: "Route" }];
  if (request.status === "awaiting_sanction" || request.status === "awaiting_cancellation_sanction") {
    return [{ decision: "approve", label: "Approve" }, { decision: "reject", label: "Reject", color: "red" }];
  }
  if (request.status === "awaiting_resumption_review") return [{ decision: "review", label: "Complete review" }];
  return [];
}

const categories = [
  { value: "CL", label: "Casual Leave (CL)" },
  { value: "RH", label: "Restricted Holiday (RH)" },
  { value: "SCL", label: "Special Casual Leave (SCL)" },
  { value: "EL", label: "Earned Leave (EL)" },
  { value: "COL", label: "Commuted Leave (COL)" },
  { value: "VL", label: "Vacation Leave (VL)" },
];

function getError(error: unknown): string {
  const candidate = error as {
    response?: {
      data?: {
        detail?: string;
        error?: { message?: string };
        [key: string]: unknown;
      };
    };
  };
  const data = candidate?.response?.data;
  if (data?.detail) return data.detail;
  if (data?.error?.message) return data.error.message;
  const fieldErrors = Object.entries(data ?? {})
    .filter(([key]) => key !== "detail" && key !== "error")
    .flatMap(([field, value]) => {
      const messages = Array.isArray(value) ? value : [value];
      return messages
        .filter((message): message is string => typeof message === "string")
        .map((message) => `${field}: ${message}`);
    });
  return fieldErrors.join(" ") || "The request could not be completed. Check the API service and your access.";
}

export default function ELMPage() {
  const { pathname } = useLocation();
  const section = pathname.split("/").filter(Boolean)[1] ?? "my-requests";
  const [requests, setRequests] = useState<LeaveRequest[]>([]);
  const [policies, setPolicies] = useState<LeavePolicy[]>([]);
  const [vacationPeriods, setVacationPeriods] = useState<VacationPeriod[]>([]);
  const [calendars, setCalendars] = useState<LeaveCalendar[]>([]);
  const [hierarchies, setHierarchies] = useState<LeaveHierarchy[]>([]);
  const [balances, setBalances] = useState<LeaveBalance[]>([]);
  const [notices, setNotices] = useState<ELMNotice[]>([]);
  const [slaReminderHours, setSlaReminderHours] = useState("24");
  const [slaEscalationHours, setSlaEscalationHours] = useState("48");
  const [slaEscalationUserId, setSlaEscalationUserId] = useState("");
  const [yearEndYear, setYearEndYear] = useState(String(new Date().getFullYear() - 1));
  const [requestAction, setRequestAction] = useState<{ requestId: number; kind: "extension" | "resumption" } | null>(null);
  const [retrySubstituteIds, setRetrySubstituteIds] = useState<Record<number, string>>({});
  const [extensionStart, setExtensionStart] = useState("");
  const [extensionEnd, setExtensionEnd] = useState("");
  const [actualResumptionDate, setActualResumptionDate] = useState("");
  const [actionReason, setActionReason] = useState("");
  const [vacationName, setVacationName] = useState("");
  const [vacationStart, setVacationStart] = useState("");
  const [vacationEnd, setVacationEnd] = useState("");
  const [vacationReference, setVacationReference] = useState("");
  const [calendarName, setCalendarName] = useState("");
  const [calendarYear, setCalendarYear] = useState(String(new Date().getFullYear()));
  const [dateCalendarId, setDateCalendarId] = useState<string | null>(null);
  const [calendarDate, setCalendarDate] = useState("");
  const [calendarDateName, setCalendarDateName] = useState("");
  const [restrictedHoliday, setRestrictedHoliday] = useState(false);
  const [closedDate, setClosedDate] = useState(true);
  const [hierarchyUnit, setHierarchyUnit] = useState("");
  const [hierarchyHead, setHierarchyHead] = useState("");
  const [hierarchyEstablishment, setHierarchyEstablishment] = useState("");
  const [hierarchySanctioner, setHierarchySanctioner] = useState("");
  const [hierarchyDirector, setHierarchyDirector] = useState("");
  const [offlineApplicantId, setOfflineApplicantId] = useState("");
  const [offlineEmployeeKind, setOfflineEmployeeKind] = useState<EmployeeKind>("staff");
  const [offlineCategory, setOfflineCategory] = useState<string | null>("EL");
  const [offlineStartDate, setOfflineStartDate] = useState("");
  const [offlineEndDate, setOfflineEndDate] = useState("");
  const [offlinePurpose, setOfflinePurpose] = useState("");
  const [offlineEvidence, setOfflineEvidence] = useState("");
  const [offlineDepartment, setOfflineDepartment] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [category, setCategory] = useState<string | null>("CL");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [purpose, setPurpose] = useState("");
  const [evidenceReference, setEvidenceReference] = useState("");
  const [half, setHalf] = useState<string | null>("none");
  const [stationLeave, setStationLeave] = useState(false);
  const [stationDetails, setStationDetails] = useState("");
  const [requiresSubstitute, setRequiresSubstitute] = useState(false);
  const [substituteId, setSubstituteId] = useState("");

  const titles: Record<string, string> = {
    "my-requests": "My Leave Requests",
    apply: "Apply for Leave",
    review: "Leave Review Queue",
    admin: "ELM Administration",
  };
  const title = titles[section] ?? "Employee Leave Management";

  async function loadData() {
    setLoading(true);
    setError("");
    try {
      if (section === "admin") {
        const [policyResponse, vacationResponse, calendarResponse, hierarchyResponse, slaResponse] = await Promise.all([
          http.get<LeavePolicy[]>("/elm/policies"),
          http.get<ListResponse<VacationPeriod>>("/elm/vacation-periods"),
          http.get<LeaveCalendar[]>("/elm/calendars"),
          http.get<LeaveHierarchy[]>("/elm/hierarchy"),
          http.get<SLAConfig>("/elm/sla-config"),
        ]);
        setPolicies(policyResponse.data);
        setVacationPeriods(vacationResponse.data.results ?? []);
        setCalendars(calendarResponse.data);
        setHierarchies(hierarchyResponse.data);
        setSlaReminderHours(String(slaResponse.data.reminder_after_hours));
        setSlaEscalationHours(String(slaResponse.data.escalation_after_hours));
        setSlaEscalationUserId(slaResponse.data.escalation_user_id == null ? "" : String(slaResponse.data.escalation_user_id));
      } else if (section === "my-requests") {
        const [requestResponse, balanceResponse, noticeResponse] = await Promise.all([
          http.get<ListResponse<LeaveRequest>>("/elm/leave-requests?scope=mine"),
          http.get<ListResponse<LeaveBalance>>("/elm/balances"),
          http.get<ListResponse<ELMNotice>>("/elm/notices"),
        ]);
        setRequests(requestResponse.data.results ?? []);
        setBalances(balanceResponse.data.results ?? []);
        setNotices(noticeResponse.data.results ?? []);
      } else {
        const response = await http.get<ListResponse<LeaveRequest>>("/elm/leave-requests?scope=assigned");
        setRequests(response.data.results ?? []);
        setBalances([]);
        setNotices([]);
      }
    } catch (err) {
      setError(getError(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadData();
    // The URL determines which ELM endpoint the page loads.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [section]);

  async function submitLeave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await http.post("/elm/leave-requests", {
        category,
        start_date: startDate,
        end_date: endDate,
        cl_half: half ?? "none",
        purpose,
        evidence_reference: evidenceReference,
        station_leave: stationLeave,
        station_leave_details: stationDetails,
        requires_substitute: requiresSubstitute,
        substitute_user_id: requiresSubstitute && substituteId ? Number(substituteId) : null,
      });
      setNotice("Leave application submitted.");
      setPurpose("");
      setEvidenceReference("");
      await loadData();
    } catch (err) {
      setError(getError(err));
    } finally {
      setBusy(false);
    }
  }

  async function decide(requestId: number, decision: ReviewDecision) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await http.post(`/elm/leave-requests/${requestId}/decision`, { decision, note: "" });
      setNotice(`Decision recorded for request EL-${requestId}.`);
      await loadData();
    } catch (err) {
      setError(getError(err));
    } finally {
      setBusy(false);
    }
  }

  async function respondSubstitute(requestId: number, response: "accept" | "decline") {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await http.post(`/elm/leave-requests/${requestId}/substitute-response`, { response });
      setNotice(`Substitute response recorded for request EL-${requestId}.`);
      await loadData();
    } catch (err) {
      setError(getError(err));
    } finally {
      setBusy(false);
    }
  }

  async function withdrawRequest(requestId: number) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await http.post(`/elm/leave-requests/${requestId}/withdraw`, { reason: "Withdrawn by applicant." });
      setNotice(`Request EL-${requestId} withdrawn.`);
      await loadData();
    } catch (err) {
      setError(getError(err));
    } finally {
      setBusy(false);
    }
  }

  async function retryAfterDecline(requestId: number) {
    const rawSubstituteId = (retrySubstituteIds[requestId] ?? "").trim();
    let substituteUserId: number | null = null;
    if (rawSubstituteId) {
      const parsedId = Number(rawSubstituteId);
      if (!Number.isInteger(parsedId) || parsedId < 1 || parsedId > 2147483647) {
        setError("Replacement substitute ID must be a positive 32-bit integer, or leave it blank to continue without one.");
        return;
      }
      substituteUserId = parsedId;
    }
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await http.post(`/elm/leave-requests/${requestId}/retry`, {
        substitute_user_id: substituteUserId,
      });
      setRetrySubstituteIds((current) => ({ ...current, [requestId]: "" }));
      setNotice(substituteUserId
        ? `Replacement substitute nominated for EL-${requestId}.`
        : `Request EL-${requestId} resubmitted without a substitute.`);
      await loadData();
    } catch (err) {
      setError(getError(err));
    } finally {
      setBusy(false);
    }
  }

  async function exportRequest(requestId: number) {
    setError("");
    try {
      const response = await http.get<string>(`/elm/leave-requests/${requestId}/export`, { responseType: "text" });
      const blob = new Blob([response.data], { type: "text/plain;charset=utf-8" });
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `ELM-request-${requestId}.txt`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(getError(err));
    }
  }

  async function cancelRequest(requestId: number) {
    if (!window.confirm("Submit a cancellation request for this approved leave?")) return;
    setBusy(true);
    setError("");
    try {
      await http.post(`/elm/leave-requests/${requestId}/cancel`, { reason: "Cancellation requested by applicant." });
      setNotice(`Cancellation request created for EL-${requestId}.`);
      await loadData();
    } catch (err) {
      setError(getError(err));
    } finally {
      setBusy(false);
    }
  }

  async function submitExtension(event: FormEvent<HTMLFormElement>, requestId: number) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await http.post(`/elm/leave-requests/${requestId}/extend`, {
        start_date: extensionStart,
        end_date: extensionEnd,
        reason: actionReason,
      });
      setRequestAction(null);
      setExtensionStart("");
      setExtensionEnd("");
      setActionReason("");
      setNotice(`Extension request created for EL-${requestId}.`);
      await loadData();
    } catch (err) {
      setError(getError(err));
    } finally {
      setBusy(false);
    }
  }

  async function submitResumption(event: FormEvent<HTMLFormElement>, requestId: number) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await http.post(`/elm/leave-requests/${requestId}/resume`, {
        actual_resumption_date: actualResumptionDate,
        details: actionReason,
      });
      setRequestAction(null);
      setActualResumptionDate("");
      setActionReason("");
      setNotice(`Resumption review submitted for EL-${requestId}.`);
      await loadData();
    } catch (err) {
      setError(getError(err));
    } finally {
      setBusy(false);
    }
  }

  async function saveSlaConfig(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const reminder = Number(slaReminderHours);
    const escalation = Number(slaEscalationHours);
    const escalationUser = slaEscalationUserId.trim() ? Number(slaEscalationUserId) : null;
    if (!Number.isInteger(reminder) || !Number.isInteger(escalation)
      || (escalationUser !== null && (!Number.isInteger(escalationUser) || escalationUser < 1))) {
      setError("SLA hours must be integers and the escalation user ID must be a positive integer or blank.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await http.put("/elm/sla-config", {
        reminder_after_hours: reminder,
        escalation_after_hours: escalation,
        escalation_user_id: escalationUser,
      });
      setNotice("SLA configuration saved.");
      await loadData();
    } catch (err) {
      setError(getError(err));
    } finally {
      setBusy(false);
    }
  }

  async function processSla() {
    setBusy(true);
    setError("");
    try {
      const response = await http.post<{ events_created: number }>("/elm/sla/process", {});
      setNotice(`SLA processing complete: ${response.data.events_created} event(s) created.`);
      await loadData();
    } catch (err) {
      setError(getError(err));
    } finally {
      setBusy(false);
    }
  }

  async function processYearEnd() {
    const year = Number(yearEndYear);
    if (!Number.isInteger(year) || year < 1900 || year > 9999) {
      setError("Provide a valid calendar year.");
      return;
    }
    if (!window.confirm(`Run year-end processing for ${year}? This operation cannot be repeated for the same year.`)) return;
    setBusy(true);
    setError("");
    try {
      const response = await http.post<{ year: number; processed_accounts: number; exceptions: unknown[] }>(
        "/elm/year-end/process",
        { year },
      );
      setNotice(`Year-end ${response.data.year} complete: ${response.data.processed_accounts} account(s) processed.`);
    } catch (err) {
      setError(getError(err));
    } finally {
      setBusy(false);
    }
  }

  async function savePolicy(policy: LeavePolicy) {
    const entitlement = Number(policy.annual_entitlement);
    if (!Number.isFinite(entitlement) || entitlement < 0) {
      setError("Annual entitlement must be a non-negative number.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await http.patch(`/elm/policies/${policy.category}`, {
        annual_entitlement: entitlement,
        employee_scope: policy.employee_scope,
        carry_forward: policy.carry_forward,
        continuous_counting: policy.continuous_counting,
        medical_evidence_required: policy.medical_evidence_required,
        enabled: policy.enabled,
      });
      setNotice(`Policy ${policy.category} saved.`);
      await loadData();
    } catch (err) {
      setError(getError(err));
    } finally {
      setBusy(false);
    }
  }

  async function togglePolicy(policy: LeavePolicy) {
    setBusy(true);
    setError("");
    try {
      await http.patch(`/elm/policies/${policy.category}`, { enabled: !policy.enabled });
      setNotice(`Policy ${policy.category} updated.`);
      await loadData();
    } catch (err) {
      setError(getError(err));
    } finally {
      setBusy(false);
    }
  }

  async function createVacationPeriod(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await http.post("/elm/vacation-periods", {
        name: vacationName.trim(),
        start_date: vacationStart,
        end_date: vacationEnd,
        external_reference: vacationReference.trim(),
        active: true,
      });
      setVacationName("");
      setVacationStart("");
      setVacationEnd("");
      setVacationReference("");
      setNotice("Vacation period created.");
      await loadData();
    } catch (err) {
      setError(getError(err));
    } finally {
      setBusy(false);
    }
  }

  async function deactivateVacationPeriod(periodId: number) {
    setBusy(true);
    setError("");
    try {
      await http.delete(`/elm/vacation-periods/${periodId}`);
      setNotice("Vacation period deactivated.");
      await loadData();
    } catch (err) {
      setError(getError(err));
    } finally {
      setBusy(false);
    }
  }

  async function createCalendar(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const year = Number(calendarYear);
    if (!calendarName.trim() || !Number.isInteger(year) || year < 1900 || year > 9999) {
      setError("Provide a calendar name and a valid year.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const response = await http.post<LeaveCalendar>("/elm/calendars", { name: calendarName.trim(), year });
      setCalendarName("");
      setDateCalendarId(String(response.data.id));
      setNotice("Leave calendar created in draft status.");
      await loadData();
    } catch (err) {
      setError(getError(err));
    } finally {
      setBusy(false);
    }
  }

  async function addCalendarDate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!dateCalendarId) {
      setError("Select a calendar before adding a date.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await http.post(`/elm/calendars/${dateCalendarId}/dates`, {
        day: calendarDate,
        name: calendarDateName.trim(),
        is_restricted_holiday: restrictedHoliday,
        is_closed_day: closedDate,
      });
      setCalendarDate("");
      setCalendarDateName("");
      setRestrictedHoliday(false);
      setClosedDate(true);
      setNotice("Calendar date added.");
      await loadData();
    } catch (err) {
      setError(getError(err));
    } finally {
      setBusy(false);
    }
  }

  async function publishCalendar(calendarId: number) {
    setBusy(true);
    setError("");
    try {
      await http.post(`/elm/calendars/${calendarId}/publish`, {});
      if (dateCalendarId === String(calendarId)) setDateCalendarId(null);
      setNotice("Leave calendar published.");
      await loadData();
    } catch (err) {
      setError(getError(err));
    } finally {
      setBusy(false);
    }
  }

  async function recordOfflineLeave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const applicantId = Number(offlineApplicantId);
    if (!Number.isInteger(applicantId) || applicantId < 1 || applicantId > 2147483647) {
      setError("Applicant ID must be a positive 32-bit integer.");
      return;
    }
    if (!offlineCategory || !offlineEvidence.trim()) {
      setError("Choose a category and provide an evidence reference.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await http.post("/elm/offline-records", {
        applicant_user_id: applicantId,
        employee_kind: offlineEmployeeKind,
        category: offlineCategory,
        start_date: offlineStartDate,
        end_date: offlineEndDate,
        purpose: offlinePurpose,
        evidence_reference: offlineEvidence.trim(),
        department: offlineDepartment.trim(),
      });
      setOfflineApplicantId("");
      setOfflineStartDate("");
      setOfflineEndDate("");
      setOfflinePurpose("");
      setOfflineEvidence("");
      setNotice("Previously sanctioned leave recorded.");
    } catch (err) {
      setError(getError(err));
    } finally {
      setBusy(false);
    }
  }

  async function saveHierarchy(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!hierarchyUnit.trim()) {
      setError("Unit key is required.");
      return;
    }
    const parseId = (value: string) => {
      if (!value.trim()) return null;
      const number = Number(value);
      return Number.isInteger(number) && number > 0 ? number : NaN;
    };
    const ids = [hierarchyHead, hierarchyEstablishment, hierarchySanctioner, hierarchyDirector].map(parseId);
    if (ids.some((id) => Number.isNaN(id))) {
      setError("Hierarchy user IDs must be positive integers or blank.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await http.post("/elm/hierarchy", {
        unit_key: hierarchyUnit.trim(),
        unit_head_user_id: ids[0],
        establishment_user_id: ids[1],
        sanctioning_authority_user_id: ids[2],
        director_user_id: ids[3],
        active: true,
      });
      setNotice("Leave hierarchy saved.");
      await loadData();
    } catch (err) {
      setError(getError(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Container size="xl" py="md">
      <PageHeader title={title} subtitle="Fusion ERP · Employee Leave Management" />
      <Stack gap="md">
        {error && <Alert color="red" title="Unable to load ELM">{error}</Alert>}
        {notice && <Alert color="green" title="ELM">{notice}</Alert>}
        {section === "apply" && (
          <Card withBorder padding="lg">
            <form onSubmit={submitLeave}>
              <Stack gap="sm">
                <Select label="Leave category" data={categories} value={category} onChange={(value) => {
                  setCategory(value);
                  if (value !== "CL") setHalf("none");
                }} required />
                <Group grow>
                  <TextInput type="date" label="Start date" value={startDate} onChange={(e) => setStartDate(e.currentTarget.value)} required />
                  <TextInput type="date" label="End date" value={endDate} onChange={(e) => setEndDate(e.currentTarget.value)} required />
                </Group>
                {category === "CL" && (
                  <Select label="CL day portion" data={[{ value: "none", label: "Full day" }, { value: "first", label: "First half" }, { value: "second", label: "Second half" }]} value={half} onChange={setHalf} />
                )}
                <Textarea label="Purpose / reason" value={purpose} onChange={(e) => setPurpose(e.currentTarget.value)} maxLength={1000} required />
                {category === "COL" && (
                  <TextInput label="Medical evidence/reference" value={evidenceReference}
                    onChange={(e) => setEvidenceReference(e.currentTarget.value)} maxLength={240} required />
                )}
                <Checkbox label="Station Leave required" checked={stationLeave} onChange={(e) => setStationLeave(e.currentTarget.checked)} />
                {stationLeave && <Textarea label="Station Leave details" value={stationDetails} onChange={(e) => setStationDetails(e.currentTarget.value)} required />}
                <Checkbox label="Nominate a substitute / responsibility holder" checked={requiresSubstitute} onChange={(e) => setRequiresSubstitute(e.currentTarget.checked)} />
                {requiresSubstitute && <TextInput type="number" min={1} step={1} label="Substitute user ID" inputMode="numeric" value={substituteId} onChange={(e) => setSubstituteId(e.currentTarget.value)} required />}
                <Group justify="flex-end"><Button type="submit" loading={busy}>Submit application</Button></Group>
              </Stack>
            </form>
          </Card>
        )}
        {section === "admin" && (
          <>
            <Card withBorder padding="lg">
              <Title order={3} mb="sm">Leave policies</Title>
              {loading ? <Loader /> : policies.length ? (
                <Table striped highlightOnHover>
                  <Table.Thead><Table.Tr><Table.Th>Category</Table.Th><Table.Th>Annual entitlement</Table.Th><Table.Th>Scope</Table.Th><Table.Th>Carry forward</Table.Th><Table.Th>Continuous</Table.Th><Table.Th>Medical evidence</Table.Th><Table.Th>Status</Table.Th><Table.Th>Actions</Table.Th></Table.Tr></Table.Thead>
                  <Table.Tbody>{policies.map((policy) => (
                    <Table.Tr key={policy.id}>
                      <Table.Td>{policy.category}</Table.Td>
                      <Table.Td>
                        <TextInput type="number" min={0} value={policy.annual_entitlement}
                          onChange={(e) => {
                            const value = e.currentTarget.value;
                            setPolicies((current) => current.map((item) => item.id === policy.id
                              ? { ...item, annual_entitlement: value } : item));
                          }} />
                      </Table.Td>
                      <Table.Td>
                        <Select size="sm" data={[
                          { value: "all", label: "Faculty and staff" },
                          { value: "faculty", label: "Faculty" },
                          { value: "staff", label: "Staff" },
                        ]} value={policy.employee_scope}
                          onChange={(value) => {
                            if (value === "all" || value === "faculty" || value === "staff") {
                              setPolicies((current) => current.map((item) => item.id === policy.id
                                ? { ...item, employee_scope: value } : item));
                            }
                          }} />
                      </Table.Td>
                      <Table.Td><Checkbox checked={policy.carry_forward}
                        onChange={(e) => {
                          const checked = e.currentTarget.checked;
                          setPolicies((current) => current.map((item) => item.id === policy.id
                            ? { ...item, carry_forward: checked } : item));
                        }} /></Table.Td>
                      <Table.Td><Checkbox checked={policy.continuous_counting}
                        onChange={(e) => {
                          const checked = e.currentTarget.checked;
                          setPolicies((current) => current.map((item) => item.id === policy.id
                            ? { ...item, continuous_counting: checked } : item));
                        }} /></Table.Td>
                      <Table.Td><Checkbox checked={policy.medical_evidence_required}
                        onChange={(e) => {
                          const checked = e.currentTarget.checked;
                          setPolicies((current) => current.map((item) => item.id === policy.id
                            ? { ...item, medical_evidence_required: checked } : item));
                        }} /></Table.Td>
                      <Table.Td><Badge color={policy.enabled ? "green" : "gray"}>{policy.enabled ? "Enabled" : "Disabled"}</Badge></Table.Td>
                      <Table.Td>
                        <Group gap="xs" wrap="nowrap">
                          <Button size="xs" loading={busy} onClick={() => void savePolicy(policy)}>Save</Button>
                          <Button size="xs" variant="light" color={policy.enabled ? "red" : "green"}
                            loading={busy} onClick={() => void togglePolicy(policy)}>{policy.enabled ? "Disable" : "Enable"}</Button>
                        </Group>
                      </Table.Td>
                    </Table.Tr>
                  ))}</Table.Tbody>
                </Table>
              ) : <Text c="dimmed">No policies returned by the ELM API.</Text>}
            </Card>

            <Card withBorder padding="lg">
              <Title order={3} mb="sm">Academic vacation periods</Title>
              <form onSubmit={createVacationPeriod}>
                <Stack gap="sm">
                  <TextInput label="Name" value={vacationName} onChange={(e) => setVacationName(e.currentTarget.value)} required />
                  <Group grow>
                    <TextInput type="date" label="Start date" value={vacationStart} onChange={(e) => setVacationStart(e.currentTarget.value)} required />
                    <TextInput type="date" label="End date" value={vacationEnd} onChange={(e) => setVacationEnd(e.currentTarget.value)} required />
                  </Group>
                  <TextInput label="External calendar reference (optional)" value={vacationReference} onChange={(e) => setVacationReference(e.currentTarget.value)} />
                  <Group justify="flex-end"><Button type="submit" loading={busy}>Add vacation period</Button></Group>
                </Stack>
              </form>
              <Table mt="md" striped highlightOnHover>
                <Table.Thead><Table.Tr><Table.Th>Name</Table.Th><Table.Th>Period</Table.Th><Table.Th>State</Table.Th><Table.Th>Action</Table.Th></Table.Tr></Table.Thead>
                <Table.Tbody>{vacationPeriods.map((period) => (
                  <Table.Tr key={period.id}>
                    <Table.Td>{period.name}</Table.Td><Table.Td>{period.start_date} – {period.end_date}</Table.Td>
                    <Table.Td><Badge color={period.active ? "green" : "gray"}>{period.active ? "Active" : "Inactive"}</Badge></Table.Td>
                    <Table.Td>{period.active && <Button size="xs" color="red" variant="light" loading={busy} onClick={() => void deactivateVacationPeriod(period.id)}>Deactivate</Button>}</Table.Td>
                  </Table.Tr>
                ))}</Table.Tbody>
              </Table>
            </Card>

            <Card withBorder padding="lg">
              <Title order={3} mb="sm">Leave calendar</Title>
              <form onSubmit={createCalendar}>
                <Group align="flex-end" grow>
                  <TextInput label="Calendar name" value={calendarName} onChange={(e) => setCalendarName(e.currentTarget.value)} required />
                  <TextInput type="number" label="Year" value={calendarYear} onChange={(e) => setCalendarYear(e.currentTarget.value)} required />
                  <Button type="submit" loading={busy}>Create draft calendar</Button>
                </Group>
              </form>
              <Table mt="md" striped highlightOnHover>
                <Table.Thead><Table.Tr><Table.Th>Name</Table.Th><Table.Th>Year</Table.Th><Table.Th>Status</Table.Th><Table.Th>Action</Table.Th></Table.Tr></Table.Thead>
                <Table.Tbody>{calendars.map((calendar) => (
                  <Table.Tr key={calendar.id}>
                    <Table.Td>{calendar.name}</Table.Td><Table.Td>{calendar.year}</Table.Td><Table.Td><Badge>{calendar.status}</Badge></Table.Td>
                    <Table.Td>
                      <Group gap="xs" wrap="nowrap">
                        {calendar.status === "draft" && <Button size="xs" variant="light" onClick={() => setDateCalendarId(String(calendar.id))}>Select</Button>}
                        {calendar.status === "draft" && <Button size="xs" loading={busy} onClick={() => void publishCalendar(calendar.id)}>Publish</Button>}
                      </Group>
                    </Table.Td>
                  </Table.Tr>
                ))}</Table.Tbody>
              </Table>
              <Title order={4} mt="lg" mb="sm">Add a date to a draft calendar</Title>
              <form onSubmit={addCalendarDate}>
                <Stack gap="sm">
                  <Select label="Draft calendar" data={calendars.filter((calendar) => calendar.status === "draft").map((calendar) => ({ value: String(calendar.id), label: `${calendar.name} (${calendar.year})` }))}
                    value={dateCalendarId} onChange={setDateCalendarId} required />
                  <Group grow>
                    <TextInput type="date" label="Date" value={calendarDate} onChange={(e) => setCalendarDate(e.currentTarget.value)} required />
                    <TextInput label="Date name" value={calendarDateName} onChange={(e) => setCalendarDateName(e.currentTarget.value)} required />
                  </Group>
                  <Checkbox label="Restricted holiday" checked={restrictedHoliday} onChange={(e) => setRestrictedHoliday(e.currentTarget.checked)} />
                  <Checkbox label="Closed day (excluded from leave counting)" checked={closedDate} onChange={(e) => setClosedDate(e.currentTarget.checked)} />
                  <Group justify="flex-end"><Button type="submit" loading={busy}>Add calendar date</Button></Group>
                </Stack>
              </form>
            </Card>

            <Card withBorder padding="lg">
              <Title order={3} mb="sm">Leave hierarchy</Title>
              <form onSubmit={saveHierarchy}>
                <Stack gap="sm">
                  <TextInput label="Unit / department key (must match directory unit)" value={hierarchyUnit} onChange={(e) => setHierarchyUnit(e.currentTarget.value)} required />
                  <Group grow>
                    <TextInput type="number" label="Unit Head user ID" value={hierarchyHead} onChange={(e) => setHierarchyHead(e.currentTarget.value)} />
                    <TextInput type="number" label="Establishment user ID" value={hierarchyEstablishment} onChange={(e) => setHierarchyEstablishment(e.currentTarget.value)} />
                  </Group>
                  <Group grow>
                    <TextInput type="number" label="Sanctioning authority user ID" value={hierarchySanctioner} onChange={(e) => setHierarchySanctioner(e.currentTarget.value)} />
                    <TextInput type="number" label="Director user ID" value={hierarchyDirector} onChange={(e) => setHierarchyDirector(e.currentTarget.value)} />
                  </Group>
                  <Group justify="flex-end"><Button type="submit" loading={busy}>Save hierarchy</Button></Group>
                </Stack>
              </form>
              <Table mt="md" striped highlightOnHover>
                <Table.Thead><Table.Tr><Table.Th>Unit</Table.Th><Table.Th>Unit Head</Table.Th><Table.Th>Establishment</Table.Th><Table.Th>Sanctioner</Table.Th><Table.Th>Director</Table.Th></Table.Tr></Table.Thead>
                <Table.Tbody>{hierarchies.map((row) => (
                  <Table.Tr key={row.id}><Table.Td>{row.unit_key}</Table.Td><Table.Td>{row.unit_head_user_id ?? "—"}</Table.Td>
                    <Table.Td>{row.establishment_user_id ?? "—"}</Table.Td><Table.Td>{row.sanctioning_authority_user_id ?? "—"}</Table.Td>
                    <Table.Td>{row.director_user_id ?? "—"}</Table.Td></Table.Tr>
                ))}</Table.Tbody>
              </Table>
            </Card>

            <Card withBorder padding="lg">
              <Title order={3} mb="sm">Synchronize previously sanctioned leave</Title>
              <Text size="sm" c="dimmed">Use only for leave already approved through the institute's offline process. The record will be marked approved and its balance debited.</Text>
              <form onSubmit={recordOfflineLeave}>
                <Stack gap="sm" mt="sm">
                  <Group grow>
                    <TextInput type="number" min={1} max={2147483647} label="Applicant user ID" value={offlineApplicantId}
                      onChange={(e) => setOfflineApplicantId(e.currentTarget.value)} required />
                    <Select label="Employee kind" data={[
                      { value: "faculty", label: "Faculty" },
                      { value: "staff", label: "Staff" },
                    ]} value={offlineEmployeeKind} onChange={(value) => {
                      if (value === "faculty" || value === "staff") setOfflineEmployeeKind(value);
                    }} required />
                    <Select label="Leave category" data={categories} value={offlineCategory} onChange={setOfflineCategory} required />
                  </Group>
                  <Group grow>
                    <TextInput type="date" label="Start date" value={offlineStartDate} onChange={(e) => setOfflineStartDate(e.currentTarget.value)} required />
                    <TextInput type="date" label="End date" value={offlineEndDate} onChange={(e) => setOfflineEndDate(e.currentTarget.value)} required />
                  </Group>
                  <TextInput label="Department / unit" value={offlineDepartment} onChange={(e) => setOfflineDepartment(e.currentTarget.value)} />
                  <Textarea label="Purpose" value={offlinePurpose} onChange={(e) => setOfflinePurpose(e.currentTarget.value)} maxLength={1000} required />
                  <TextInput label="Offline sanction / evidence reference" value={offlineEvidence}
                    onChange={(e) => setOfflineEvidence(e.currentTarget.value)} maxLength={240} required />
                  <Group justify="flex-end"><Button type="submit" loading={busy}>Record approved leave</Button></Group>
                </Stack>
              </form>
            </Card>

            <Card withBorder padding="lg">
              <Title order={3} mb="sm">SLA reminders and escalation</Title>
              <form onSubmit={saveSlaConfig}>
                <Stack gap="sm">
                  <Group grow>
                    <TextInput type="number" min={1} label="Reminder after (hours)" value={slaReminderHours}
                      onChange={(e) => setSlaReminderHours(e.currentTarget.value)} required />
                    <TextInput type="number" min={2} label="Escalation after (hours)" value={slaEscalationHours}
                      onChange={(e) => setSlaEscalationHours(e.currentTarget.value)} required />
                  </Group>
                  <TextInput type="number" min={1} label="Escalation user ID (optional)" value={slaEscalationUserId}
                    onChange={(e) => setSlaEscalationUserId(e.currentTarget.value)} />
                  <Group justify="flex-end">
                    <Button type="submit" loading={busy}>Save SLA settings</Button>
                    <Button type="button" variant="light" loading={busy} onClick={() => void processSla()}>Process SLA reminders</Button>
                  </Group>
                </Stack>
              </form>
            </Card>

            <Card withBorder padding="lg">
              <Title order={3} mb="sm">Year-end balance processing</Title>
              <Text size="sm" c="dimmed">Year-end runs are recorded once per year. Confirm carefully before processing.</Text>
              <Group align="flex-end" mt="sm">
                <TextInput type="number" label="Year to process" value={yearEndYear}
                  onChange={(e) => setYearEndYear(e.currentTarget.value)} />
                <Button color="orange" loading={busy} onClick={() => void processYearEnd()}>Run year-end process</Button>
              </Group>
            </Card>
          </>
        )}
        {section === "my-requests" && (
          <Card withBorder padding="lg">
            <Title order={3} mb="sm">Leave balances</Title>
            {loading ? <Loader /> : balances.length ? (
              <Table striped highlightOnHover>
                <Table.Thead><Table.Tr><Table.Th>Category</Table.Th><Table.Th>Entitlement</Table.Th><Table.Th>Carried in</Table.Th><Table.Th>Consumed</Table.Th><Table.Th>Available</Table.Th></Table.Tr></Table.Thead>
                <Table.Tbody>{balances.map((balance) => (
                  <Table.Tr key={`${balance.year}-${balance.category}`}>
                    <Table.Td>{balance.category}</Table.Td><Table.Td>{balance.entitlement}</Table.Td>
                    <Table.Td>{balance.carried_in}</Table.Td><Table.Td>{balance.consumed}</Table.Td><Table.Td>{balance.available}</Table.Td>
                  </Table.Tr>
                ))}</Table.Tbody>
              </Table>
            ) : <Text c="dimmed">No leave balances returned by the ELM API.</Text>}
          </Card>
        )}
        {section === "my-requests" && (
          <Card withBorder padding="lg">
            <Title order={3} mb="sm">Notifications</Title>
            {loading ? <Loader /> : notices.length ? notices.map((item) => (
              <Group key={item.id} justify="space-between" align="flex-start" py="xs">
                <Stack gap={2}>
                  <Text size="sm" fw={500}>{item.kind.replaceAll("_", " ")}</Text>
                  <Text size="sm">{item.message}</Text>
                </Stack>
                <Text c="dimmed" size="xs">{new Date(item.created_at).toLocaleString()}</Text>
              </Group>
            )) : <Text c="dimmed">No notifications.</Text>}
          </Card>
        )}
        {(section === "my-requests" || section === "review") && (
          <>
            <Group justify="space-between"><Text c="dimmed">{section === "review" ? "Requests available to your role" : "Your submitted leave requests"}</Text><Button variant="light" onClick={() => void loadData()} loading={loading}>Refresh</Button></Group>
            {loading ? <Loader /> : requests.length ? requests.map((request) => (
              <Card key={request.id} withBorder padding="md">
                <Group justify="space-between" align="flex-start">
                  <Stack gap={4}>
                    <Title order={4}>EL-{request.id} · {request.category}</Title>
                    <Text size="sm">{request.start_date} – {request.end_date} · {request.requested_days} day(s)</Text>
                    <Text size="sm">{request.purpose}</Text>
                  </Stack>
                  <Badge>{request.status.replaceAll("_", " ")}</Badge>
                </Group>
                {section === "my-requests" && (
                  <Group mt="md" justify="flex-end">
                    <Button size="xs" variant="light" loading={busy} onClick={() => void exportRequest(request.id)}>Export</Button>
                    {request.status.startsWith("awaiting_") || request.status === "action_required" ? (
                      <Button size="xs" color="red" variant="light" loading={busy}
                        onClick={() => void withdrawRequest(request.id)}>Withdraw request</Button>
                    ) : null}
                    {request.status === "approved"
                      && ["leave", "offline", "extension"].includes(request.request_type) && (
                      <>
                        <Button size="xs" color="red" variant="light" loading={busy} onClick={() => void cancelRequest(request.id)}>Request cancellation</Button>
                        {(request.category === "EL" || request.category === "COL" || request.category === "VL") && (
                          <>
                            <Button size="xs" variant="light" onClick={() => setRequestAction(
                              requestAction?.requestId === request.id && requestAction.kind === "extension" ? null : { requestId: request.id, kind: "extension" },
                            )}>Request extension</Button>
                            <Button size="xs" variant="light" onClick={() => setRequestAction(
                              requestAction?.requestId === request.id && requestAction.kind === "resumption" ? null : { requestId: request.id, kind: "resumption" },
                            )}>Submit resumption</Button>
                          </>
                        )}
                      </>
                    )}
                  </Group>
                )}
                {section === "my-requests" && request.status === "action_required" && (
                  <Stack mt="md" gap="xs">
                    <Text size="sm" c="dimmed">
                      The nominated substitute declined. Enter a replacement user ID, or leave it blank to continue without a substitute.
                    </Text>
                    <Group align="flex-end">
                      <TextInput type="number" min={1} max={2147483647} step={1}
                        label="Replacement substitute user ID (optional)"
                        value={retrySubstituteIds[request.id] ?? ""}
                        onChange={(e) => {
                          const value = e.currentTarget.value;
                          setRetrySubstituteIds((current) => ({ ...current, [request.id]: value }));
                        }} />
                      <Button size="xs" loading={busy} onClick={() => void retryAfterDecline(request.id)}>
                        Retry request
                      </Button>
                    </Group>
                  </Stack>
                )}
                {section === "my-requests" && requestAction?.requestId === request.id && requestAction.kind === "extension" && (
                  <form onSubmit={(event) => void submitExtension(event, request.id)}>
                    <Stack mt="md" gap="sm">
                      <Title order={5}>Extension period</Title>
                      <Group grow>
                        <TextInput type="date" label="Extension start" value={extensionStart} onChange={(e) => setExtensionStart(e.currentTarget.value)} required />
                        <TextInput type="date" label="Extension end" value={extensionEnd} onChange={(e) => setExtensionEnd(e.currentTarget.value)} required />
                      </Group>
                      <Textarea label="Reason (optional)" value={actionReason} onChange={(e) => setActionReason(e.currentTarget.value)} />
                      <Group justify="flex-end"><Button type="submit" size="xs" loading={busy}>Submit extension</Button></Group>
                    </Stack>
                  </form>
                )}
                {section === "my-requests" && requestAction?.requestId === request.id && requestAction.kind === "resumption" && (
                  <form onSubmit={(event) => void submitResumption(event, request.id)}>
                    <Stack mt="md" gap="sm">
                      <Title order={5}>Resumption details</Title>
                      <TextInput type="date" label="Actual resumption date" value={actualResumptionDate}
                        onChange={(e) => setActualResumptionDate(e.currentTarget.value)} required />
                      <Textarea label="Details (optional)" value={actionReason} onChange={(e) => setActionReason(e.currentTarget.value)} />
                      <Group justify="flex-end"><Button type="submit" size="xs" loading={busy}>Submit resumption</Button></Group>
                    </Stack>
                  </form>
                )}
                {section === "review" && (
                  <Group mt="md" justify="flex-end">
                    {request.status === "awaiting_substitute" && request.current_assignee_user_id != null ? (
                      <>
                        <Button size="xs" loading={busy} onClick={() => void respondSubstitute(request.id, "accept")}>Accept substitute</Button>
                        <Button size="xs" color="red" variant="light" loading={busy} onClick={() => void respondSubstitute(request.id, "decline")}>Decline substitute</Button>
                      </>
                    ) : request.status === "awaiting_substitute" ? (
                      <Text size="sm" c="red">This request has no assigned substitute. An ELM administrator must correct its routing.</Text>
                    ) : reviewActions(request).map((action) => (
                      <Button key={action.decision} size="xs" color={action.color} variant={action.color ? "light" : "filled"}
                        loading={busy} onClick={() => void decide(request.id, action.decision)}>{action.label}</Button>
                    ))}
                  </Group>
                )}
              </Card>
            )) : <Text c="dimmed">No leave requests to display.</Text>}
          </>
        )}
      </Stack>
    </Container>
  );
}
