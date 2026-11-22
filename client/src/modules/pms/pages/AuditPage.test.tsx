import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AuditPage from "./AuditPage";

const hooks = vi.hoisted(() => ({ usePmsAudit: vi.fn() }));
vi.mock("../api/hooks", () => hooks);

describe("AuditPage", () => {
  beforeEach(() => hooks.usePmsAudit.mockReturnValue({ data: [], isPending: false, error: null }));

  it("shows loading, empty, and API error states", () => {
    hooks.usePmsAudit.mockReturnValueOnce({ data: undefined, isPending: true, error: null });
    const { rerender, container } = render(<MantineProvider><AuditPage /></MantineProvider>);
    expect(container.querySelector(".mantine-Loader-root")).toBeInTheDocument();

    hooks.usePmsAudit.mockReturnValueOnce({ data: [], isPending: false, error: null });
    rerender(<MantineProvider><AuditPage /></MantineProvider>);
    expect(screen.getByText("No audit records")).toBeInTheDocument();

    hooks.usePmsAudit.mockReturnValueOnce({
      data: undefined, isPending: false,
      error: { response: { data: { error: { message: "Audit service unavailable" } } } },
    });
    rerender(<MantineProvider><AuditPage /></MantineProvider>);
    expect(screen.getByText("Audit service unavailable")).toBeInTheDocument();
  });

  it("applies an application filter to the audit query", async () => {
    const user = userEvent.setup();
    render(<MantineProvider><AuditPage /></MantineProvider>);
    await user.type(screen.getByLabelText("Application ID"), "41");
    await user.click(screen.getByRole("button", { name: "Apply filter" }));
    expect(hooks.usePmsAudit).toHaveBeenLastCalledWith(41);
  });
});
