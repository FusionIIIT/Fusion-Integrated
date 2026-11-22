import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { beforeAll, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import { PersonPicker } from "./PersonPicker";

function Harness({ start = null as number | null, initialLabel = "" }) {
  const [value, setValue] = useState<number | null>(start);
  return (
    <>
      <PersonPicker label="Coordinator" kind="student" value={value} onChange={setValue}
        initialLabel={initialLabel} />
      <output aria-label="chosen">{value ?? "none"}</output>
    </>
  );
}

function renderPicker(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<MantineProvider><QueryClientProvider client={qc}>{ui}</QueryClientProvider>
  </MantineProvider>);
}

describe("PersonPicker", () => {
  // jsdom has no scrollIntoView; Mantine calls it on the already-chosen option when it opens.
  beforeAll(() => {
    if (!Element.prototype.scrollIntoView) Element.prototype.scrollIntoView = () => undefined;
  });

  it("keeps the chosen person after the box fills with their name", async () => {
    const get = vi.spyOn(http, "get").mockResolvedValue({ data: [
      { user_id: 3, username: "stu00003", display_name: "Asha", kind: "student" }] });
    renderPicker(<Harness />);
    await userEvent.type(screen.getByRole("textbox", { name: "Coordinator" }), "stu00003");
    await userEvent.click(await screen.findByRole("option", { name: "Asha (stu00003)",
      hidden: true }));
    expect(screen.getByLabelText("chosen")).toHaveTextContent("3");
    expect(screen.getByRole("textbox", { name: "Coordinator" })).toHaveValue("Asha (stu00003)");
    await waitFor(() => expect(get).toHaveBeenCalled());
    expect(get).not.toHaveBeenCalledWith("/gymkhana/people",
      { params: { q: "Asha (stu00003)", kind: "student" } });
  });

  it("shows a current holder by name without searching", () => {
    const get = vi.spyOn(http, "get");
    get.mockClear();
    renderPicker(<Harness start={7} initialLabel="Ravi (stu00007)" />);
    expect(screen.getByRole("textbox", { name: "Coordinator" })).toHaveValue("Ravi (stu00007)");
    expect(get).not.toHaveBeenCalled();
  });

  it("keeps the current holder when they are picked again", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: [
      { user_id: 7, username: "stu00007", display_name: "Ravi", kind: "student" }] });
    renderPicker(<Harness start={7} initialLabel="Ravi (stu00007)" />);
    const box = screen.getByRole("textbox", { name: "Coordinator" });
    await userEvent.clear(box);
    await userEvent.type(box, "stu00007");
    await userEvent.click(await screen.findByRole("option", { name: "Ravi (stu00007)",
      hidden: true }));
    expect(screen.getByLabelText("chosen")).toHaveTextContent("7");
  });
});
