import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import MaterialsPage from "./MaterialsPage";

const hooks = vi.hoisted(() => ({
  useCourses: vi.fn(),
  useMaterials: vi.fn(),
  useCreateMaterial: vi.fn(),
  useDeleteMaterial: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

const useAuth = vi.hoisted(() => vi.fn());
vi.mock("../../../auth/AuthProvider", () => ({ useAuth }));

const sampleCourse = {
  id: 1,
  course_id: 101,
  course_code: "CS101",
  title: "Introduction to Computer Science",
  role: "STUDENT",
};

const sampleMaterial = {
  id: 1,
  course_id: 101,
  title: "Lecture 1 Slides",
  description: "Introductory slides",
  material_type: "FILE",
  content_text: "",
  external_url: "",
  file_attachment: "/media/lms/materials/lec1.pdf",
  section_name: "Week 1",
  sort_order: 1,
  status: "PUBLISHED",
  release_date: null,
  uploaded_by: 1,
  created_at: "2026-11-01",
};

describe("MaterialsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    hooks.useCourses.mockReturnValue({ data: [sampleCourse], isPending: false });
    hooks.useCreateMaterial.mockReturnValue({ mutate: vi.fn(), isPending: false });
    hooks.useDeleteMaterial.mockReturnValue({ mutate: vi.fn(), isPending: false });
  });

  it("renders loading state while materials are loading", () => {
    useAuth.mockReturnValue({ can: () => false });
    hooks.useMaterials.mockReturnValue({ data: null, isPending: true, error: null });

    render(
      <MantineProvider>
        <MaterialsPage />
      </MantineProvider>
    );

    expect(screen.getByText(/loading materials/i)).toBeInTheDocument();
  });

  it("renders empty state when course has no materials", () => {
    useAuth.mockReturnValue({ can: () => false });
    hooks.useMaterials.mockReturnValue({ data: [], isPending: false, error: null });

    render(
      <MantineProvider>
        <MaterialsPage />
      </MantineProvider>
    );

    expect(screen.getByText(/no course materials available/i)).toBeInTheDocument();
  });

  it("renders error state on fetch failure", () => {
    useAuth.mockReturnValue({ can: () => false });
    hooks.useMaterials.mockReturnValue({
      data: null,
      isPending: false,
      error: new Error("Server error"),
    });

    render(
      <MantineProvider>
        <MaterialsPage />
      </MantineProvider>
    );

    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
  });

  it("shows Add Material button for users holding lms.material.create", () => {
    useAuth.mockReturnValue({ can: (p: string) => p === "lms.material.create" });
    hooks.useMaterials.mockReturnValue({ data: [sampleMaterial], isPending: false, error: null });

    render(
      <MantineProvider>
        <MaterialsPage />
      </MantineProvider>
    );

    expect(screen.getByText("Lecture 1 Slides")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /add material/i })).toBeInTheDocument();
  });

  it("hides Add Material button when user lacks lms.material.create", () => {
    useAuth.mockReturnValue({ can: () => false });
    hooks.useMaterials.mockReturnValue({ data: [sampleMaterial], isPending: false, error: null });

    render(
      <MantineProvider>
        <MaterialsPage />
      </MantineProvider>
    );

    expect(screen.getByText("Lecture 1 Slides")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /add material/i })).toBeNull();
  });
});
