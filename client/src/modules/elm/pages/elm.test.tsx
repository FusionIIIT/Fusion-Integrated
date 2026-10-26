import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { http } from "../../../lib/http";
import { ApplyLeavePage } from "./ApplyLeavePage";
import { LeaveApprovalsPage } from "./LeaveApprovalsPage";

function mount(page: React.ReactNode) {
  return render(<MantineProvider><MemoryRouter>{page}</MemoryRouter></MantineProvider>);
}

describe("Leave application",()=>{
  it("offers both CL half-day sessions",()=>{
    mount(<ApplyLeavePage/>);
    fireEvent.click(screen.getByLabelText("Half-day CL"));
    expect(screen.getByRole("option",{name:"First half"})).toBeInTheDocument();
    expect(screen.getByRole("option",{name:"Second half"})).toBeInTheDocument();
  });
  it("removes the CL-only half-day option after category changes",()=>{
    mount(<ApplyLeavePage/>);
    fireEvent.click(screen.getByLabelText("Half-day CL"));
    fireEvent.change(screen.getByLabelText("Leave category"),{target:{value:"EL"}});
    expect(screen.queryByLabelText("Half-day CL")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Session")).not.toBeInTheDocument();
  });
  it("requires station dates and address together",()=>{
    mount(<ApplyLeavePage/>);
    fireEvent.click(screen.getByLabelText("Leaving Jabalpur during this leave"));
    expect(screen.getByLabelText("Contact address")).toBeRequired();
    expect(screen.getByLabelText("Departure")).toBeRequired();
    expect(screen.getByLabelText("Return")).toBeRequired();
  });
});

describe("Approval decisions",()=>{
  it("presents higher leave Unit Head decisions as recommendations", async()=>{
    vi.spyOn(http,"get").mockResolvedValue({data:[{id:"request",applicant_user_id:"1",leave_type:"EL",request_kind:"LEAVE",status:"PENDING_UNIT_HEAD",start_date:"2026-10-27",end_date:"2026-10-27",duration_days:"1",reason:"Appointment"}]});
    mount(<LeaveApprovalsPage/>);
    await waitFor(()=>expect(screen.getByRole("button",{name:"Recommend"})).toBeInTheDocument());
    expect(screen.getByRole("button",{name:"Do not recommend"})).toBeInTheDocument();
    expect(screen.queryByRole("button",{name:"Reject"})).not.toBeInTheDocument();
  });
});
