import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import CreateFilePage from "./CreateFilePage";

const hooks = vi.hoisted(() => ({
  useCreateFile: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

describe("CreateFilePage", () => {
  const mockCreateMutate = vi.fn();

  beforeEach(() => {
    mockCreateMutate.mockReset();
    hooks.useCreateFile.mockReturnValue({
      mutate: mockCreateMutate,
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

  it("switches to save as draft mode and submits valid draft payload", () => {
    render(
      <MantineProvider>
        <MemoryRouter>
          <CreateFilePage />
        </MemoryRouter>
      </MantineProvider>,
    );

    const draftRadio = screen.getByLabelText(/save as draft/i);
    fireEvent.click(draftRadio);

    const submitBtn = screen.getByRole("button", { name: /save as draft/i });
    expect(submitBtn).toBeInTheDocument();

    const subjectInput = screen.getByLabelText(/subject/i);
    const commentInput = screen.getByLabelText(/initial note \/ remarks/i);

    fireEvent.change(subjectInput, { target: { value: "New Research Grant" } });
    fireEvent.change(commentInput, { target: { value: "Initial draft notes." } });

    fireEvent.click(submitBtn);

    expect(mockCreateMutate).toHaveBeenCalledWith(
      expect.objectContaining({
        subject: "New Research Grant",
        comment: "Initial draft notes.",
        is_draft: true,
      }),
      expect.any(Object),
    );
  });
});
