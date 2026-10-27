import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { LeaveConfiguration, LeaveRecords, Requests } from "./pages";
import type { Configuration, LeaveApplication } from "./api";

const mocks = vi.hoisted(() => ({auth:vi.fn(), query:vi.fn(), mutate:vi.fn()}));
vi.mock("../../auth/AuthProvider", () => ({useAuth:mocks.auth}));
vi.mock("./api", () => ({useElmQuery:mocks.query, useElmWrite:()=>({mutateAsync:mocks.mutate, isPending:false})}));
vi.mock("@mantine/notifications", () => ({notifications:{show:vi.fn()}}));

const config: Configuration = {
  policy:{non_working_weekdays:[6], require_col_evidence:true, reminder_hours:12, escalation_hours:72},
  employees:[{user_id:1, unit:"Saved unit", designation:"Staff", coverage_required:false,
    eligible_categories:["CL","EL"], routes:{
      CL:[{stage:"unit_head",user_id:2,role:"Unit Head",escalation_user_id:7,escalation_role:"Unit Head",reassign_on_escalation:true}],
      EL:[{stage:"unit_head",user_id:2,role:"Unit Head"},{stage:"sanction",user_id:3,role:"Registrar"}],
    }}], calendars:[], attendance_outbox:[],
};
const record: LeaveApplication = {
  id:8, user_id:1, kind:"leave", parent_id:null, category:"CL", start_date:"2026-11-02", end_date:"2026-11-02",
  effective_end_date:"2026-11-02", half:"full", reason:"Recorded leave", station_leave:false,
  station_details:"", status:"approved", revision:1, substitute_id:null, offline_reference:"ORDER/OLD",
  resumption_reviewed:false, days_by_year:{"2026":"1"}, allowed_actions:[], history:[],
};
const emptyPage = {results:[], next:null, previous:null};
let records: LeaveApplication[];
let can: (permission:string)=>boolean;

beforeEach(() => {
  vi.clearAllMocks(); records=[]; can=()=>true;
  mocks.auth.mockImplementation(()=>({session:{user:{id:7}}, can}));
  mocks.mutate.mockResolvedValue({});
  mocks.query.mockImplementation((path:string)=>({isPending:false, data:
    path === "employees/" ? [1,2,3,7].map((id)=>({user_id:id, display_name:`Employee ${id}`, kind:"staff"})) :
    path === "configuration/" ? config : {...emptyPage, results:records},
  }));
});

function show(component: React.ReactNode) {
  return render(<MantineProvider>{component}</MantineProvider>);
}
async function pick(label:string, name:string) {
  await userEvent.click(screen.getByRole("textbox", {name:label}));
  await userEvent.click(await screen.findByRole("option", {name}));
}

describe("ELM administration", () => {
  it("loads and saves current policy instead of overwriting it with defaults", async () => {
    show(<LeaveConfiguration />);
    expect(screen.getByRole("textbox", {name:"Reminder after hours"})).toHaveValue("12");
    expect(screen.getByRole("checkbox", {name:"Require medical evidence for COL"})).toBeChecked();
    fireEvent.click(screen.getByRole("button", {name:"Save policy"}));
    await waitFor(()=>expect(mocks.mutate).toHaveBeenCalledWith({path:"configuration/", method:"put", data:{policy:config.policy}}));
  });

  it("preserves category-specific routes and escalation when only the unit is edited", async () => {
    show(<LeaveConfiguration />);
    await pick("Employee", "Employee 1 (1)");
    expect(screen.getByRole("textbox", {name:"Organizational unit"})).toHaveValue("Saved unit");
    fireEvent.change(screen.getByRole("textbox", {name:"Organizational unit"}), {target:{value:"New unit"}});
    fireEvent.click(screen.getByRole("button", {name:"Save employee hierarchy"}));
    await waitFor(()=>expect(mocks.mutate).toHaveBeenCalledWith({path:"configuration/", method:"put", data:{employee:{...config.employees[0], unit:"New unit"}}}));
  });

  it("restricts record entry to the authorized role", () => {
    can=()=>false;
    show(<LeaveRecords />);
    expect(screen.getByText("Your active role cannot maintain leave records.")).toBeInTheDocument();
    expect(screen.queryByRole("button", {name:"Record offline-sanctioned leave"})).toBeNull();
    expect(mocks.query).toHaveBeenCalledWith("applications/", false);
  });

  it("submits existing sanction evidence without creating an approval request", async () => {
    show(<LeaveRecords />);
    fireEvent.click(screen.getByRole("button", {name:"Record offline-sanctioned leave"}));
    const dialog = within(await screen.findByRole("dialog"));
    expect(dialog.getByRole("button", {name:"Record sanctioned leave"})).toBeDisabled();
    await pick("Employee", "Employee 1 (1)");
    await pick("Sanctioning authority", "Employee 2 (2)");
    for (const [label, value] of [["Start date","2026-11-02"],["End date","2026-11-02"],["Leave purpose","Medical visit"],["Existing sanction reference","ORDER/1"],["Why ELM was unavailable","Network outage"]] as const) {
      fireEvent.change(dialog.getByLabelText(label), {target:{value}});
    }
    fireEvent.click(dialog.getByRole("button", {name:"Record sanctioned leave"}));
    await waitFor(()=>expect(mocks.mutate).toHaveBeenCalledWith({path:"offline/", data:{
      user_id:1, category:"CL", start_date:"2026-11-02", end_date:"2026-11-02", half:"full",
      reason:"Medical visit", offline_reference:"ORDER/1", unavailability_reason:"Network outage",
      authority_id:2, authority_role:"Unit Head", station_leave:false, station_details:"", medical_reference:"",
    }}));
  });

  it("sends only the reference and reason for an administrative correction", async () => {
    records=[record]; show(<LeaveRecords />);
    fireEvent.click(screen.getByRole("button", {name:"Correct reference"}));
    const dialog=within(await screen.findByRole("dialog"));
    fireEvent.change(dialog.getByLabelText("Corrected reference"), {target:{value:"ORDER/NEW"}});
    fireEvent.change(dialog.getByLabelText("Correction reason"), {target:{value:"Clerical correction"}});
    fireEvent.click(dialog.getByRole("button", {name:"Save reference correction"}));
    await waitFor(()=>expect(mocks.mutate).toHaveBeenCalledWith({path:"applications/8/correction/", data:{reference:"ORDER/NEW", reason:"Clerical correction"}}));
  });

  it("requests the owner's history before server pagination", () => {
    show(<Requests />);
    expect(mocks.query).toHaveBeenCalledWith("applications/?scope=mine", true);
  });
});
