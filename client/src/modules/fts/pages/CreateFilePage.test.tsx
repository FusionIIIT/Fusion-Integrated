import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import CreateFilePage from "./CreateFilePage";

const hooks = vi.hoisted(() => ({
  useCreateFile: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

describe("CreateFilePage", () => {
  beforeEach(() => {
    hooks.useCreateFile.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    });
  });

  it("renders creation form inputs and buttons", () => {
    render(
      <MantineProvider>
        <MemoryRouter>
          <CreateFilePage />
        </MemoryRouter>
      </MantineProvider>,
    );

    expect(screen.getByText("Create Institute File")).toBeInTheDocument();
    expect(screen.getByLabelText(/subject/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/description/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/initial note \/ remarks/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /circulate file/i })).toBeInTheDocument();
  });
});
