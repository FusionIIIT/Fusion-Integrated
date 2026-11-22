/** Every IAA page: its loading, empty and error states, the control a role must not see,
 *  and the main action. Hooks and the session are replaced; the pages are real. */
import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type {
  Anomaly, Dashboard, FinancialRecord, Observation, Summary,
} from "../api/types";
import AnomaliesPage from "./AnomaliesPage";
import ApprovalsPage from "./ApprovalsPage";
import ConfigurationPage from "./ConfigurationPage";
import FinanceReviewPage from "./FinanceReviewPage";
import MyRequestsPage from "./MyRequestsPage";
import NotificationsPage from "./NotificationsPage";
import ObservationsPage from "./ObservationsPage";
import ReportsPage from "./ReportsPage";

const hooks = vi.hoisted(() => ({
  useRecords: vi.fn(), useRecord: vi.fn(), useHistory: vi.fn(), useCreateRecord: vi.fn(),
  useAddDocument: vi.fn(), useSubmit: vi.fn(), useAnswerQuery: vi.fn(), useRaiseQuery: vi.fn(),
  useValidate: vi.fn(), useDecide: vi.fn(), useProcess: vi.fn(),
  useAnomalies: vi.fn(), useFlagAnomaly: vi.fn(), useAnomalyAction: vi.fn(),
  useObservations: vi.fn(), useRaiseObservation: vi.fn(), useRespondObservation: vi.fn(),
  useReviewObservation: vi.fn(),
  useSummary: vi.fn(), useExport: vi.fn(), useDashboard: vi.fn(),
  usePolicies: vi.fn(), usePublishPolicy: vi.fn(), useYears: vi.fn(), useAddYear: vi.fn(),
  useBudget: vi.fn(), useAddBudgetEntry: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

const auth = vi.hoisted(() => ({ useAuth: vi.fn() }));
vi.mock("../../../auth/AuthProvider", () => auth);

vi.mock("../components/toast", () => ({ done: vi.fn(), failed: vi.fn() }));

const FAILURE = new Error("down");
const idle = () => ({ mutate: vi.fn(), mutateAsync: vi.fn().mockResolvedValue({}),
                      isPending: false, error: null });
const ready = <T,>(data: T) => ({ data, isPending: false, error: null });
const loading = { data: undefined, isPending: true, error: null };
const broken = { data: undefined, isPending: false, error: FAILURE };

function holding(permissions: string[], user = 7, role = "iaa_finance_staff") {
  auth.useAuth.mockReturnValue({
    can: (p: string) => permissions.includes(p),
    session: { user: { id: user }, active_role: role },
  });
}

function show(page: React.ReactElement) {
  return render(<MantineProvider>{page}</MantineProvider>);
}

const row = (over: Partial<FinancialRecord> = {}) => ({
  id: 41, kind: "expense", status: "submitted", user_id: 9, department: "CSE",
  request_type: "voucher", title: "Lab kits", description: "", amount: "10000.00",
  purpose: "", trip_start: null, trip_end: null, financial_year: "2026-27",
  submitted_at: null, route_levels: [], current_level: null, processing_reference: "",
  processing_note: "", processed_at: null, created_at: "2026-11-01", updated_at: "2026-11-01",
  ...over,
}) as FinancialRecord;

beforeEach(() => {
  for (const hook of Object.values(hooks)) hook.mockReset();
  for (const name of ["useCreateRecord", "useAddDocument", "useSubmit", "useAnswerQuery",
    "useRaiseQuery", "useValidate", "useDecide", "useProcess", "useFlagAnomaly",
    "useAnomalyAction", "useRaiseObservation", "useRespondObservation",
    "useReviewObservation", "useExport", "usePublishPolicy", "useAddYear",
    "useAddBudgetEntry"] as const) hooks[name].mockReturnValue(idle());
  hooks.useRecord.mockReturnValue({ data: undefined, error: null });
  hooks.useHistory.mockReturnValue({ data: [] });
  hooks.usePolicies.mockReturnValue({ data: [], error: null });
  hooks.useYears.mockReturnValue({ data: [] });
  hooks.useBudget.mockReturnValue({ data: { results: [] } });
  holding([]);
});

describe("MyRequestsPage", () => {
  it("says it is loading", () => {
    hooks.useRecords.mockReturnValue(loading);
    show(<MyRequestsPage />);
    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });

  it("has an empty state", () => {
    hooks.useRecords.mockReturnValue(ready({ results: [] }));
    show(<MyRequestsPage />);
    expect(screen.getByText("You have no requests or claims yet")).toBeInTheDocument();
  });

  it("shows the server's failure and nothing to press", () => {
    hooks.useRecords.mockReturnValue(broken);
    show(<MyRequestsPage />);
    expect(screen.getByText("Could not load this")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "New" })).toBeNull();
  });

  it("lists the rows and opens the new-request form from the main action", async () => {
    hooks.useRecords.mockReturnValue(ready({ results: [row()] }));
    show(<MyRequestsPage />);
    expect(screen.getByRole("row", { name: "Open request 41" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "New" }));
    expect(await screen.findByText("New expense / voucher request")).toBeInTheDocument();
  });
});

describe("FinanceReviewPage", () => {
  it("has loading, empty and error states", () => {
    hooks.useRecords.mockReturnValue(loading);
    const first = show(<FinanceReviewPage />);
    expect(screen.getByText("Loading…")).toBeInTheDocument();
    first.unmount();

    hooks.useRecords.mockReturnValue(ready({ results: [] }));
    const second = show(<FinanceReviewPage />);
    expect(screen.getByText("Nothing is waiting here")).toBeInTheDocument();
    second.unmount();

    hooks.useRecords.mockReturnValue(broken);
    show(<FinanceReviewPage />);
    expect(screen.getByText("Could not load this")).toBeInTheDocument();
  });

  it("switches to the queue of items to record", async () => {
    hooks.useRecords.mockReturnValue(ready({ results: [] }));
    show(<FinanceReviewPage />);
    expect(hooks.useRecords).toHaveBeenLastCalledWith({ queue: "finance_review" });
    await userEvent.click(screen.getByText("To record"));
    expect(hooks.useRecords).toHaveBeenLastCalledWith({ queue: "to_record" });
  });
});

describe("ApprovalsPage", () => {
  it("has loading, empty and error states", () => {
    hooks.useRecords.mockReturnValue(loading);
    const first = show(<ApprovalsPage />);
    expect(screen.getByText("Loading…")).toBeInTheDocument();
    first.unmount();

    hooks.useRecords.mockReturnValue(ready({ results: [] }));
    const second = show(<ApprovalsPage />);
    expect(screen.getByText("Nothing is waiting on your role")).toBeInTheDocument();
    second.unmount();

    hooks.useRecords.mockReturnValue(broken);
    show(<ApprovalsPage />);
    expect(screen.getByText("Could not load this")).toBeInTheDocument();
  });

  it("asks only for the approver's queue and opens an item with the keyboard", async () => {
    hooks.useRecords.mockReturnValue(ready({ results: [row({ status: "finance_validated" })] }));
    show(<ApprovalsPage />);
    expect(hooks.useRecords).toHaveBeenCalledWith({ queue: "pending_approval" });
    screen.getByRole("row", { name: "Open request 41" }).focus();
    await userEvent.keyboard("{Enter}");
    expect(hooks.useRecord).toHaveBeenLastCalledWith(41);
  });
});

const anomaly = (over: Partial<Anomaly> = {}) => ({
  id: 5, record: 41, category: "budget", source: "automatic", description: "Short by 10000",
  status: "open", resolver_chain: ["iaa_finance_staff", "iaa_dean"], resolver_level: 0,
  assigned_role: "iaa_finance_staff", raised_role: "system", resolved_role: "",
  resolved_at: null, resolution: "", created_at: "2026-11-01", ...over,
}) as Anomaly;

describe("AnomaliesPage", () => {
  it("has loading, empty and error states", () => {
    hooks.useAnomalies.mockReturnValue(loading);
    const first = show(<AnomaliesPage />);
    expect(screen.getByText("Loading…")).toBeInTheDocument();
    first.unmount();

    hooks.useAnomalies.mockReturnValue(ready({ results: [] }));
    const second = show(<AnomaliesPage />);
    expect(screen.getByText("No anomalies in your scope")).toBeInTheDocument();
    second.unmount();

    hooks.useAnomalies.mockReturnValue(broken);
    show(<AnomaliesPage />);
    expect(screen.getByText("Could not load this")).toBeInTheDocument();
  });

  it("hides Flag anomaly from a role without the permission, and shows it to one with it", () => {
    hooks.useAnomalies.mockReturnValue(ready({ results: [] }));
    holding(["iaa.anomaly.view"]);
    const first = show(<AnomaliesPage />);
    expect(screen.queryByRole("button", { name: /flag anomaly/i })).toBeNull();
    first.unmount();

    holding(["iaa.anomaly.view", "iaa.anomaly.create"]);
    show(<AnomaliesPage />);
    expect(screen.getByRole("button", { name: /flag anomaly/i })).toBeInTheDocument();
  });

  it("offers Resolve only to the assigned role, and only with text", async () => {
    const act = idle();
    hooks.useAnomalyAction.mockReturnValue(act);
    hooks.useAnomalies.mockReturnValue(ready({ results: [anomaly()] }));

    holding(["iaa.anomaly.view", "iaa.anomaly.review"], 7, "iaa_dean");   // not the assignee
    const other = show(<AnomaliesPage />);
    expect(screen.queryByRole("button", { name: "Resolve" })).toBeNull();
    other.unmount();

    holding(["iaa.anomaly.view"], 7, "iaa_finance_staff");               // assignee, no permission
    const noCode = show(<AnomaliesPage />);
    expect(screen.queryByRole("button", { name: "Resolve" })).toBeNull();
    noCode.unmount();

    holding(["iaa.anomaly.view", "iaa.anomaly.review"], 7, "iaa_finance_staff");
    show(<AnomaliesPage />);
    expect(screen.getByRole("button", { name: "Resolve" })).toBeDisabled();
    await userEvent.type(screen.getByLabelText("Resolution or escalation reason"), "Reallocated");
    await userEvent.click(screen.getByRole("button", { name: "Resolve" }));
    expect(act.mutateAsync).toHaveBeenCalledWith(
      { id: 5, action: "resolve", text: "Reallocated" });
  });

  it("offers Escalate only while a further resolver exists", () => {
    holding(["iaa.anomaly.view", "iaa.anomaly.review"], 7, "iaa_dean");
    hooks.useAnomalies.mockReturnValue(ready({ results: [anomaly({
      assigned_role: "iaa_dean", resolver_level: 1 })] }));
    show(<AnomaliesPage />);
    expect(screen.getByRole("button", { name: "Resolve" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Escalate" })).toBeNull();
  });
});

const observation = (over: Partial<Observation> = {}) => ({
  id: 3, record: 41, respondent_user_id: 7, title: "Missing note", detail: "No sign-off",
  status: "open", cycle: 1, raised_role: "iaa_auditor", created_at: "2026-11-01",
  responses: [], ...over,
}) as Observation;

describe("ObservationsPage", () => {
  it("has loading, empty and error states", () => {
    hooks.useObservations.mockReturnValue(loading);
    const first = show(<ObservationsPage />);
    expect(screen.getByText("Loading…")).toBeInTheDocument();
    first.unmount();

    hooks.useObservations.mockReturnValue(ready({ results: [] }));
    const second = show(<ObservationsPage />);
    expect(screen.getByText("No audit observations")).toBeInTheDocument();
    second.unmount();

    hooks.useObservations.mockReturnValue(broken);
    show(<ObservationsPage />);
    expect(screen.getByText("Could not load this")).toBeInTheDocument();
  });

  it("hides Raise observation from anyone who may not raise one", () => {
    hooks.useObservations.mockReturnValue(ready({ results: [] }));
    holding(["iaa.observation.view"]);
    const first = show(<ObservationsPage />);
    expect(screen.queryByRole("button", { name: /raise observation/i })).toBeNull();
    first.unmount();

    holding(["iaa.observation.view", "iaa.observation.create"]);
    show(<ObservationsPage />);
    expect(screen.getByRole("button", { name: /raise observation/i })).toBeInTheDocument();
  });

  it("lets only the respondent answer, and sends the corrective action", async () => {
    const respond = idle();
    hooks.useRespondObservation.mockReturnValue(respond);
    hooks.useObservations.mockReturnValue(ready({ results: [observation()] }));

    holding(["iaa.observation.view", "iaa.observation.update"], 8);       // someone else
    const other = show(<ObservationsPage />);
    expect(screen.queryByRole("button", { name: "Send response" })).toBeNull();
    other.unmount();

    holding(["iaa.observation.view", "iaa.observation.update"], 7);
    show(<ObservationsPage />);
    expect(screen.getByRole("button", { name: "Send response" })).toBeDisabled();
    await userEvent.type(screen.getByLabelText("Corrective action taken"), "Added the note");
    await userEvent.click(screen.getByRole("button", { name: "Send response" }));
    expect(respond.mutateAsync).toHaveBeenCalledWith(
      { id: 3, corrective_action: "Added the note", evidence_link: "" });
  });

  it("lets only a reviewer close a responded observation", () => {
    hooks.useObservations.mockReturnValue(ready({ results: [observation({
      status: "responded" })] }));
    holding(["iaa.observation.view"], 4, "iaa_auditor");
    const without = show(<ObservationsPage />);
    expect(screen.queryByRole("button", { name: "Record review" })).toBeNull();
    without.unmount();

    holding(["iaa.observation.view", "iaa.observation.review"], 4, "iaa_auditor");
    show(<ObservationsPage />);
    expect(screen.getByRole("button", { name: "Record review" })).toBeEnabled();
  });
});

const summary: Summary = {
  records: [{ kind: "expense", status: "approved", count: 3 }],
  approval_turnaround: [{ designation: "iaa_hod", decisions: 3, average_hours: 2.5 }],
  anomalies: [], observations: [],
};

describe("ReportsPage", () => {
  it("has loading and error states", () => {
    hooks.useSummary.mockReturnValue(loading);
    const first = show(<ReportsPage />);
    expect(screen.getByText("Loading…")).toBeInTheDocument();
    first.unmount();

    hooks.useSummary.mockReturnValue(broken);
    show(<ReportsPage />);
    expect(screen.getByText("Could not load this")).toBeInTheDocument();
  });

  it("says plainly when a section is empty", () => {
    hooks.useSummary.mockReturnValue(ready(summary));
    show(<ReportsPage />);
    expect(screen.getAllByText("Nothing in your scope.")).toHaveLength(2);
    expect(screen.getByText("iaa_hod")).toBeInTheDocument();
  });

  it("hides the export from a role without it, and runs it for one with it", async () => {
    const exporter = idle();
    hooks.useExport.mockReturnValue(exporter);
    hooks.useSummary.mockReturnValue(ready(summary));
    holding(["iaa.report.view"]);
    const first = show(<ReportsPage />);
    expect(screen.queryByRole("button", { name: /export csv/i })).toBeNull();
    first.unmount();

    holding(["iaa.report.view", "iaa.report.export"]);
    show(<ReportsPage />);
    await userEvent.click(screen.getByRole("button", { name: /export csv/i }));
    expect(exporter.mutateAsync).toHaveBeenCalledTimes(1);
  });
});

const dashboard: Dashboard = {
  pending: { to_review: 2, to_approve: 0 },
  notifications: [{ id: 1, kind: "submitted", message: "Request #41 was submitted",
                    entity: "record", entity_id: 41, created_at: "2026-11-01T10:00:00Z" }],
};

describe("NotificationsPage", () => {
  it("has loading, empty and error states", () => {
    hooks.useDashboard.mockReturnValue(loading);
    const first = show(<NotificationsPage />);
    expect(screen.getByText("Loading…")).toBeInTheDocument();
    first.unmount();

    hooks.useDashboard.mockReturnValue(ready({ pending: {}, notifications: [] }));
    const second = show(<NotificationsPage />);
    expect(screen.getByText("No notifications yet")).toBeInTheDocument();
    expect(screen.getByText("No pending actions.")).toBeInTheDocument();
    second.unmount();

    hooks.useDashboard.mockReturnValue(broken);
    show(<NotificationsPage />);
    expect(screen.getByText("Could not load this")).toBeInTheDocument();
  });

  it("lists what is pending and what happened", () => {
    hooks.useDashboard.mockReturnValue(ready(dashboard));
    show(<NotificationsPage />);
    expect(screen.getByText("to review: 2")).toBeInTheDocument();
    expect(screen.getByText("Request #41 was submitted")).toBeInTheDocument();
  });
});

describe("ConfigurationPage", () => {
  it("shows the state of an unconfigured module", () => {
    holding(["iaa.configuration.view"]);
    show(<ConfigurationPage />);
    expect(screen.getByText(/No policy published yet/)).toBeInTheDocument();
    expect(screen.getByText("None yet.")).toBeInTheDocument();
  });

  it("is read-only without the update permission", () => {
    holding(["iaa.configuration.view"]);
    show(<ConfigurationPage />);
    expect(screen.queryByRole("button", { name: "Publish" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Add" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Add entry" })).toBeNull();
  });

  it("publishes the policy text for a role that may update it", async () => {
    const publish = idle();
    hooks.usePublishPolicy.mockReturnValue(publish);
    holding(["iaa.configuration.view", "iaa.configuration.update"]);
    show(<ConfigurationPage />);
    await userEvent.click(screen.getByRole("button", { name: "Publish" }));
    expect(publish.mutateAsync).toHaveBeenCalledWith(
      expect.objectContaining({ approval_timeout_hours: 48 }));
  });

  it("refuses to publish text that is not JSON", async () => {
    holding(["iaa.configuration.view", "iaa.configuration.update"]);
    show(<ConfigurationPage />);
    const box = screen.getByLabelText(/New version \(JSON\)/);
    await userEvent.clear(box);
    await userEvent.type(box, "not json");
    expect(screen.getByText("Not valid JSON")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Publish" })).toBeDisabled();
  });

  it("shows a policy-load failure instead of an empty form", () => {
    hooks.usePolicies.mockReturnValue({ data: undefined, error: FAILURE });
    holding(["iaa.configuration.view"]);
    show(<ConfigurationPage />);
    expect(screen.getByText("Could not load this")).toBeInTheDocument();
  });
});
