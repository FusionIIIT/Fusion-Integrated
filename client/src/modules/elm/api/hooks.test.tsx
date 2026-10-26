import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { http } from "../../../lib/http";
import { useMyLeaves, submitLeave, followupLeave, replaceSubstitute } from "./hooks";

describe("ELM integration", () => {
  it("uses paths relative to the shared API base", async () => {
    vi.spyOn(http,"get").mockResolvedValue({data: []});
    const {result}=renderHook(()=>useMyLeaves());
    await waitFor(()=>expect(result.current.loading).toBe(false));
    expect(http.get).toHaveBeenCalledWith("/elm/leaves/");
  });
  it("shows the platform error message as text", async () => {
    vi.spyOn(http,"get").mockRejectedValue({response:{data:{error:{message:"ELM access denied",details:[]}}}});
    const {result}=renderHook(()=>useMyLeaves());
    await waitFor(()=>expect(result.current.loading).toBe(false));
    expect(result.current.error).toBe("ELM access denied");
  });
  it("lets the server calculate duration", async () => {
    vi.spyOn(http,"post").mockResolvedValue({data:{id:"request"}});
    await submitLeave({leave_type:"CL",start_date:"2026-10-27",end_date:"2026-10-27",reason:"Appointment"});
    expect(http.post).toHaveBeenCalledWith("/elm/leaves/",expect.not.objectContaining({duration_days:expect.anything()}));
  });
  it("creates a follow-up without modifying the approved application", async () => {
    vi.spyOn(http,"post").mockResolvedValue({data:{id:"follow-up"}});
    await followupLeave("original","cancel",{reason:"Plans changed"});
    expect(http.post).toHaveBeenCalledWith("/elm/leaves/original/cancel/",{reason:"Plans changed"});
  });
  it("sends a replacement nomination through its dedicated action", async () => {
    vi.spyOn(http,"post").mockResolvedValue({data:{id:"request"}});
    await replaceSubstitute("request","42");
    expect(http.post).toHaveBeenCalledWith("/elm/leaves/request/replace-substitute/",{substitute_id:"42"});
  });
});
