import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AnnouncementsPage from "./AnnouncementsPage";

const hooks = vi.hoisted(() => ({
  useCourses: vi.fn(),
  useAnnouncements: vi.fn(),
  useCreateAnnouncement: vi.fn(),
  useDeleteAnnouncement: vi.fn(),
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

const sampleAnnouncement = {
  id: 1,
  course_id: 101,
  title: "Midterm Schedule Announced",
  content: "The midterm will be held on Friday at 10 AM.",
  author_id: 1,
  author_role: "INSTRUCTOR",
  created_at: "2026-11-05T09:00:00Z",
};

describe("AnnouncementsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    hooks.useCourses.mockReturnValue({ data: [sampleCourse], isPending: false });
    hooks.useCreateAnnouncement.mockReturnValue({ mutate: vi.fn(), isPending: false });
    hooks.useDeleteAnnouncement.mockReturnValue({ mutate: vi.fn(), isPending: false });
  });

  it("renders loading state while announcements load", () => {
    useAuth.mockReturnValue({ can: () => false });
    hooks.useAnnouncements.mockReturnValue({ data: null, isPending: true, error: null });

    render(
      <MantineProvider>
        <AnnouncementsPage />
      </MantineProvider>
    );

    expect(screen.getByText(/loading announcements/i)).toBeInTheDocument();
  });

  it("renders empty state when there are no announcements", () => {
    useAuth.mockReturnValue({ can: () => false });
    hooks.useAnnouncements.mockReturnValue({ data: [], isPending: false, error: null });

    render(
      <MantineProvider>
        <AnnouncementsPage />
      </MantineProvider>
    );

    expect(screen.getByText(/no announcements posted/i)).toBeInTheDocument();
  });

  it("renders error state when fetch fails", () => {
    useAuth.mockReturnValue({ can: () => false });
    hooks.useAnnouncements.mockReturnValue({
      data: null,
      isPending: false,
      error: new Error("Failed"),
    });

    render(
      <MantineProvider>
        <AnnouncementsPage />
      </MantineProvider>
    );

    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
  });

  it("shows Post Announcement button when user has lms.announcement.create", () => {
    useAuth.mockReturnValue({ can: (p: string) => p === "lms.announcement.create" });
    hooks.useAnnouncements.mockReturnValue({
      data: [sampleAnnouncement],
      isPending: false,
      error: null,
    });

    render(
      <MantineProvider>
        <AnnouncementsPage />
      </MantineProvider>
    );

    expect(screen.getByText("Midterm Schedule Announced")).toBeInTheDocument();
    expect(screen.getByText(/The midterm will be held on Friday/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /new announcement/i })).toBeInTheDocument();
  });

  it("hides Post Announcement button when user lacks lms.announcement.create", () => {
    useAuth.mockReturnValue({ can: () => false });
    hooks.useAnnouncements.mockReturnValue({
      data: [sampleAnnouncement],
      isPending: false,
      error: null,
    });

    render(
      <MantineProvider>
        <AnnouncementsPage />
      </MantineProvider>
    );

    expect(screen.getByText("Midterm Schedule Announced")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /new announcement/i })).toBeNull();
  });
});
