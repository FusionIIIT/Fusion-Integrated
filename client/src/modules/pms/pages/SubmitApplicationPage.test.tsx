import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import SubmitApplicationPage from "./SubmitApplicationPage";

const hooks = vi.hoisted(() => ({ usePmsAction: vi.fn() }));
const auth = vi.hoisted(() => ({ session: { user: { id: 7, display_name: "Applicant", email: "applicant@example.test" } } }));
vi.mock("../api/hooks", () => hooks);
vi.mock("../../../auth/AuthProvider", () => ({ useAuth: () => auth }));

function renderPage() {
  return render(<MantineProvider><MemoryRouter><SubmitApplicationPage /></MemoryRouter></MantineProvider>);
}

async function completeRequiredFields(user: ReturnType<typeof userEvent.setup>) {
  const fields = screen.getAllByRole("textbox");
  await user.type(fields[0]!, "Thermal storage controller");
  await user.type(fields[1]!, "Energy Systems");
  await user.type(fields[2]!, "Stores heat for later use.");
  await user.type(fields[3]!, "A detailed description of the invention.");
  await user.type(fields[4]!, "A thermal storage controller.");
}

describe("SubmitApplicationPage (UC-PMS-001)", () => {
  const mutate = vi.fn();
  beforeEach(() => {
    mutate.mockReset();
    hooks.usePmsAction.mockReturnValue({ mutate, isPending: false, error: null });
  });

  it("validates required invention data and ownership before enabling submission", async () => {
    const user = userEvent.setup();
    renderPage();
    const submit = screen.getByRole("button", { name: "Submit application" });
    expect(submit).toBeDisabled();

    await completeRequiredFields(user);
    expect(submit).toBeEnabled();
    expect(mutate).not.toHaveBeenCalled();
  });

  it("sends a valid application through the PMS action hook", async () => {
    const user = userEvent.setup();
    renderPage();
    await completeRequiredFields(user);
    await user.click(screen.getByRole("button", { name: "Submit application" }));
    expect(mutate).toHaveBeenCalledWith(expect.objectContaining({
      title: "Thermal storage controller", domain: "Energy Systems", jurisdiction: "IN",
    }), expect.objectContaining({ onSuccess: expect.any(Function) }));
  });

  it("shows server validation errors", () => {
    hooks.usePmsAction.mockReturnValue({
      mutate, isPending: false,
      error: { response: { data: { error: { message: "Submission was rejected" } } } },
    });
    renderPage();
    expect(screen.getByText("Submission was rejected")).toBeInTheDocument();
  });
});
