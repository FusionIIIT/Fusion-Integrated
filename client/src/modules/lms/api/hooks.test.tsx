import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import {
  getApiErrorMessage,
  getFileDownloadUrl,
  useCourse,
  useCourses,
  useCourseAssignments,
  useCourseAnnouncements,
  useCourseMaterials,
  useCourseSections,
  useAssignmentSubmissions,
  useGrades,
  useGradeAuditLogs,
  useScheduledReleases,
  useSubmitAssignment,
  useGradeSubmission,
} from "./hooks";
import type {
  Course,
  Assignment,
  Submission,
  Grade,
  ScheduledRelease,
} from "./types";

function createWrapper() {
  const qc = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

describe("LMS API Hooks & Utilities", () => {
  describe("Utility Functions", () => {
    it("getFileDownloadUrl returns download query URL", () => {
      expect(getFileDownloadUrl("assignments/test.pdf")).toBe(
        "/api/v1/lms/files/download/?key=assignments%2Ftest.pdf"
      );
    });

    it("getApiErrorMessage handles DRF nested error envelope", () => {
      const err = {
        response: {
          data: {
            error: {
              code: "policy_denied",
              message: "Submissions past deadline require instructor approval",
              details: [{ message: "Late policy gating active" }],
            },
          },
        },
      };
      expect(getApiErrorMessage(err)).toBe("Late policy gating active");
    });

    it("getApiErrorMessage handles simple detail string", () => {
      const err = {
        response: {
          data: {
            detail: "Course not found",
          },
        },
      };
      expect(getApiErrorMessage(err)).toBe("Course not found");
    });

    it("getApiErrorMessage falls back to default message", () => {
      const err = new Error("Network error");
      expect(getApiErrorMessage(err)).toBe("Something went wrong. Please try again.");
    });
  });

  describe("Query Hooks", () => {
    it("useCourses fetches course list", async () => {
      const mockCourses: Partial<Course>[] = [
        { id: 1, code: "CS101", name: "Intro to CS" },
      ];
      vi.spyOn(http, "get").mockResolvedValueOnce({ data: mockCourses });

      const { result } = renderHook(() => useCourses(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual(mockCourses);
      expect(http.get).toHaveBeenCalledWith("/lms/courses/");
    });

    it("useCourse fetches single course details", async () => {
      const mockCourse: Partial<Course> = {
        id: 42,
        code: "CS201",
        name: "Data Structures",
      };
      vi.spyOn(http, "get").mockResolvedValueOnce({ data: mockCourse });

      const { result } = renderHook(() => useCourse(42), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual(mockCourse);
      expect(http.get).toHaveBeenCalledWith("/lms/courses/42/");
    });

    it("useCourseAssignments fetches assignments for a course", async () => {
      const mockAssignments: Partial<Assignment>[] = [
        { id: 10, title: "Lab 1", points_possible: 100 },
      ];
      vi.spyOn(http, "get").mockResolvedValueOnce({ data: mockAssignments });

      const { result } = renderHook(() => useCourseAssignments(42), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual(mockAssignments);
      expect(http.get).toHaveBeenCalledWith("/lms/courses/42/assignments/");
    });

    it("useCourseMaterials fetches materials for a course", async () => {
      vi.spyOn(http, "get").mockResolvedValueOnce({ data: [] });

      const { result } = renderHook(() => useCourseMaterials(42), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(http.get).toHaveBeenCalledWith("/lms/materials/?course=42");
    });

    it("useCourseSections fetches sections for a course", async () => {
      vi.spyOn(http, "get").mockResolvedValueOnce({ data: [] });

      const { result } = renderHook(() => useCourseSections(42), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(http.get).toHaveBeenCalledWith("/lms/courses/42/sections/");
    });

    it("useCourseAnnouncements fetches announcements for a course", async () => {
      vi.spyOn(http, "get").mockResolvedValueOnce({ data: [] });

      const { result } = renderHook(() => useCourseAnnouncements(42), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(http.get).toHaveBeenCalledWith("/lms/courses/42/announcements/");
    });

    it("useAssignmentSubmissions fetches submissions for an assignment", async () => {
      const mockSubmissions: Partial<Submission>[] = [
        { id: 101, assignment: 10, student_user_id: 5, version: 1 },
      ];
      vi.spyOn(http, "get").mockResolvedValueOnce({ data: mockSubmissions });

      const { result } = renderHook(() => useAssignmentSubmissions(10), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual(mockSubmissions);
      expect(http.get).toHaveBeenCalledWith("/lms/assignments/10/submissions/");
    });

    it("useGrades fetches grades list", async () => {
      const mockGrades: Partial<Grade>[] = [
        { id: 50, points_awarded: 95, is_draft: false },
      ];
      vi.spyOn(http, "get").mockResolvedValueOnce({ data: mockGrades });

      const { result } = renderHook(() => useGrades(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual(mockGrades);
      expect(http.get).toHaveBeenCalledWith("/lms/grades/");
    });

    it("useGradeAuditLogs fetches audit history for a grade", async () => {
      vi.spyOn(http, "get").mockResolvedValueOnce({ data: [] });

      const { result } = renderHook(() => useGradeAuditLogs(50), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(http.get).toHaveBeenCalledWith("/lms/grades/50/audit_logs/");
    });

    it("useScheduledReleases fetches scheduled releases list", async () => {
      const mockReleases: Partial<ScheduledRelease>[] = [
        { id: 1, scheduled_publish_at: "2026-11-05T00:00:00Z" },
      ];
      vi.spyOn(http, "get").mockResolvedValueOnce({ data: mockReleases });

      const { result } = renderHook(() => useScheduledReleases(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual(mockReleases);
      expect(http.get).toHaveBeenCalledWith("/lms/scheduled-releases/");
    });
  });

  describe("Mutation Hooks", () => {
    it("useSubmitAssignment posts submission payload", async () => {
      const mockResponse: Partial<Submission> = {
        id: 201,
        assignment: 10,
        submission_type: "text",
        content_text: "My final solution",
      };
      vi.spyOn(http, "post").mockResolvedValueOnce({ data: mockResponse });

      const { result } = renderHook(() => useSubmitAssignment(10), {
        wrapper: createWrapper(),
      });

      result.current.mutate({
        submission_type: "text",
        content_text: "My final solution",
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(http.post).toHaveBeenCalledWith("/lms/assignments/10/submit/", {
        submission_type: "text",
        content_text: "My final solution",
      });
    });

    it("useGradeSubmission posts grade evaluation payload", async () => {
      const mockGrade: Partial<Grade> = {
        id: 301,
        submission: 201,
        points_awarded: 88,
        is_draft: true,
      };
      vi.spyOn(http, "post").mockResolvedValueOnce({ data: mockGrade });

      const { result } = renderHook(() => useGradeSubmission(201), {
        wrapper: createWrapper(),
      });

      result.current.mutate({
        points: 88,
        feedback: "Great work on problem 1",
        action: "draft",
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(http.post).toHaveBeenCalledWith("/lms/submissions/201/grade/", {
        points: 88,
        feedback: "Great work on problem 1",
        action: "draft",
      });
    });
  });
});
