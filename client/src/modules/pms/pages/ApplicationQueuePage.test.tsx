import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { application } from "./pageTestFixtures";
import ApplicationQueuePage from "./ApplicationQueuePage";

const hooks = vi.hoisted(() => ({
  usePmsApplications: vi.fn(), usePmsApplication: vi.fn(),
  usePmsAction: vi.fn(() => ({ mutate: vi.fn(), isPending: false, error: null })),
}));
vi.mock("../api/hooks", () => hooks);

describe("ApplicationQueuePage (UC-PMS-005)", () => {
  beforeEach(() => {
    hooks.usePmsApplications.mockReturnValue({ data: [application], isPending: false, error: null });
    hooks.usePmsApplication.mockReturnValue({ data: undefined, isPending: false, error: null });
  });

  it("renders loading, empty, and error states", () => {
    hooks.usePmsApplications.mockReturnValue({ data: undefined, isPending: true, error: null });
    const { rerender, container } = render(<MantineProvider><MemoryRouter><ApplicationQueuePage /></MemoryRouter></MantineProvider>);
    expect(container.querySelector(".mantine-Loader-root")).toBeInTheDocument();
    hooks.usePmsApplications.mockReturnValue({ data: [], isPending: false, error: null });
    rerender(<MantineProvider><MemoryRouter><ApplicationQueuePage /></MemoryRouter></MantineProvider>);
    expect(screen.getByText("Queue is empty")).toBeInTheDocument();
    hooks.usePmsApplications.mockReturnValue({
      data: undefined, isPending: false,
      error: { response: { data: { error: { message: "Queue unavailable" } } } },
    });
    rerender(<MantineProvider><MemoryRouter><ApplicationQueuePage /></MemoryRouter></MantineProvider>);
    expect(screen.getByText("Queue unavailable")).toBeInTheDocument();
  });

  it("opens an application and exposes its assignment action", async () => {
    hooks.usePmsApplication.mockReturnValue({ data: application, isPending: false, error: null });
    render(<MantineProvider><MemoryRouter><ApplicationQueuePage /></MemoryRouter></MantineProvider>);
    fireEvent.click(screen.getByRole("button", { name: "Manage" }));
    expect(screen.getByRole("button", { name: "Assign Director" })).toBeInTheDocument();
  });
});
