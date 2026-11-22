import { describe, expect, it, vi } from "vitest";

import { api } from "../../../lib/api";
import {
  createAnnouncement,
  createAssignment,
  createMaterial,
  deleteAnnouncement,
  deleteAssignment,
  deleteMaterial,
  gradeSubmission,
  releaseGrades,
  submitAssignment,
  updateAnnouncement,
  updateAssignment,
  updateWorkspace,
} from "./hooks";

describe("courses api client", () => {
  it("updateWorkspace calls PATCH with correct endpoint and payload", async () => {
    const mockData = {
      id: 1,
      code: "CS201",
      title: "Data Structures Updated",
      description: "Updated Description",
      semester: "Autumn 2026",
      academic_year: "2026-2027",
      credits: 4,
      syllabus: "New Syllabus",
      schedule: "Mon/Wed 10:00 AM",
      is_published: true,
      allow_ta_announcements: false,
      instructors: [],
      tas: [],
      viewer_role: "instructor" as const,
      can_manage: true,
    };

    const patchSpy = vi.spyOn(api, "patch").mockResolvedValue({
      data: mockData,
    });

    const payload = {
      title: "Data Structures Updated",
      syllabus: "New Syllabus",
    };

    const res = await updateWorkspace(1, payload);

    expect(patchSpy).toHaveBeenCalledWith("/api/v1/courses/workspaces/1", payload);
    expect(res).toEqual(mockData);
  });

  it("createAnnouncement calls POST with correct endpoint and payload", async () => {
    const mockAnnouncement = {
      id: 10,
      workspace_id: 1,
      title: "Exam Notice",
      body: "Midterm exam will be next Monday.",
      is_published: true,
      published_at: "2026-11-09T10:00:00Z",
      created_by_id: 10,
      author_name: "Prof. Turing",
      created_at: "2026-11-09T10:00:00Z",
      updated_at: "2026-11-09T10:00:00Z",
    };

    const postSpy = vi.spyOn(api, "post").mockResolvedValue({
      data: mockAnnouncement,
    });

    const payload = {
      title: "Exam Notice",
      body: "Midterm exam will be next Monday.",
      is_published: true,
    };

    const res = await createAnnouncement(1, payload);

    expect(postSpy).toHaveBeenCalledWith(
      "/api/v1/courses/workspaces/1/announcements",
      payload,
    );
    expect(res).toEqual(mockAnnouncement);
  });

  it("updateAnnouncement calls PATCH with correct endpoint and payload", async () => {
    const mockUpdated = {
      id: 10,
      workspace_id: 1,
      title: "Updated Exam Notice",
      body: "Updated body",
      is_published: true,
      published_at: "2026-11-09T10:00:00Z",
      created_by_id: 10,
      author_name: "Prof. Turing",
      created_at: "2026-11-09T10:00:00Z",
      updated_at: "2026-11-09T11:00:00Z",
    };

    const patchSpy = vi.spyOn(api, "patch").mockResolvedValue({
      data: mockUpdated,
    });

    const payload = { title: "Updated Exam Notice", body: "Updated body" };
    const res = await updateAnnouncement(1, 10, payload);

    expect(patchSpy).toHaveBeenCalledWith(
      "/api/v1/courses/workspaces/1/announcements/10",
      payload,
    );
    expect(res).toEqual(mockUpdated);
  });

  it("deleteAnnouncement calls DELETE with correct endpoint", async () => {
    const deleteSpy = vi.spyOn(api, "delete").mockResolvedValue({ data: null });
    await deleteAnnouncement(1, 10);
    expect(deleteSpy).toHaveBeenCalledWith(
      "/api/v1/courses/workspaces/1/announcements/10",
    );
  });

  it("createMaterial and deleteMaterial call correct endpoints", async () => {
    const mockMat = {
      id: 5,
      workspace_id: 1,
      section: null,
      section_title: null,
      title: "Lecture 1 Notes",
      description: "",
      material_type: "note" as const,
      file_url: null,
      filename: "",
      file_size: 0,
      mime_type: "",
      link_url: "",
      content: "Trees",
      is_published: true,
      release_at: null,
      is_available: true,
      is_scheduled: false,
      created_by_id: 10,
      sort_order: 0,
      created_at: "2026-11-09T10:00:00Z",
      updated_at: "2026-11-09T10:00:00Z",
    };

    const postSpy = vi.spyOn(api, "post").mockResolvedValue({ data: mockMat });
    const deleteSpy = vi.spyOn(api, "delete").mockResolvedValue({ data: null });

    const payload = {
      title: "Lecture 1 Notes",
      material_type: "note" as const,
      content: "Trees",
    };

    const res = await createMaterial(1, payload);
    expect(postSpy).toHaveBeenCalledWith(
      "/api/v1/courses/workspaces/1/materials",
      payload,
    );
    expect(res).toEqual(mockMat);

    await deleteMaterial(1, 5);
    expect(deleteSpy).toHaveBeenCalledWith(
      "/api/v1/courses/workspaces/1/materials/5",
    );
  });

  it("createAssignment, updateAssignment, and deleteAssignment call correct endpoints", async () => {
    const mockAsgn = {
      id: 7,
      workspace_id: 1,
      title: "Lab 1",
      description: "Trees",
      instructions: "C++",
      is_published: false,
      published_at: null,
      created_by_id: 10,
      author_name: "Prof. Turing",
      created_at: "2026-11-09T10:00:00Z",
      updated_at: "2026-11-09T10:00:00Z",
    };

    const postSpy = vi.spyOn(api, "post").mockResolvedValue({ data: mockAsgn });
    const patchSpy = vi.spyOn(api, "patch").mockResolvedValue({
      data: { ...mockAsgn, is_published: true },
    });
    const deleteSpy = vi.spyOn(api, "delete").mockResolvedValue({ data: null });

    const createPayload = {
      title: "Lab 1",
      description: "Trees",
      instructions: "C++",
      is_published: false,
    };

    const created = await createAssignment(1, createPayload);
    expect(postSpy).toHaveBeenCalledWith(
      "/api/v1/courses/workspaces/1/assignments",
      createPayload,
    );
    expect(created).toEqual(mockAsgn);

    const updatePayload = { is_published: true };
    const updated = await updateAssignment(1, 7, updatePayload);
    expect(patchSpy).toHaveBeenCalledWith(
      "/api/v1/courses/workspaces/1/assignments/7",
      updatePayload,
    );
    expect(updated.is_published).toBe(true);

    await deleteAssignment(1, 7);
    expect(deleteSpy).toHaveBeenCalledWith(
      "/api/v1/courses/workspaces/1/assignments/7",
    );
  });

  it("handles assignment deadline configuration and clearing payloads", async () => {
    const mockDeadlineAsgn = {
      id: 8,
      workspace_id: 1,
      title: "Lab 2: Graphs",
      description: "Graph search",
      instructions: "Python",
      due_at: "2026-11-20T23:59:59Z",
      has_passed: false,
      is_published: true,
      published_at: "2026-11-09T10:00:00Z",
      created_by_id: 10,
      author_name: "Prof. Turing",
      created_at: "2026-11-09T10:00:00Z",
      updated_at: "2026-11-09T10:00:00Z",
    };

    const postSpy = vi.spyOn(api, "post").mockResolvedValue({ data: mockDeadlineAsgn });
    const patchSpy = vi.spyOn(api, "patch").mockResolvedValue({
      data: { ...mockDeadlineAsgn, due_at: null, has_passed: false },
    });

    const createPayload = {
      title: "Lab 2: Graphs",
      due_at: "2026-11-20T23:59:59Z",
      is_published: true,
    };
    const created = await createAssignment(1, createPayload);
    expect(postSpy).toHaveBeenCalledWith(
      "/api/v1/courses/workspaces/1/assignments",
      createPayload,
    );
    expect(created.due_at).toBe("2026-11-20T23:59:59Z");
    expect(created.has_passed).toBe(false);

    // Clear deadline payload
    const clearPayload = { clear_due_at: true, due_at: null };
    const updated = await updateAssignment(1, 8, clearPayload);
    expect(patchSpy).toHaveBeenCalledWith(
      "/api/v1/courses/workspaces/1/assignments/8",
      clearPayload,
    );
    expect(updated.due_at).toBeNull();
  });

  it("submitAssignment calls POST with multipart FormData", async () => {
    const mockSubmission = {
      id: 1,
      assignment_id: 10,
      workspace_id: 1,
      student_id: 30,
      student_name: "Student Thirty",
      student_username: "24BCS227",
      submission_type: "file" as const,
      filename: "lab1.pdf",
      file_size: 1024,
      file_url: "/api/v1/courses/workspaces/1/assignments/10/submissions/1/download",
      link_url: "",
      content: "Submitted work",
      submitted_at: "2026-11-10T14:00:00Z",
      is_late: false,
      attempt_number: 1,
      status: "submitted" as const,
      created_at: "2026-11-10T14:00:00Z",
      updated_at: "2026-11-10T14:00:00Z",
    };

    const postSpy = vi.spyOn(api, "post").mockResolvedValue({ data: mockSubmission });
    const dummyFile = new File(["dummy content"], "lab1.pdf", { type: "application/pdf" });

    const payload = {
      submission_type: "file" as const,
      file: dummyFile,
      content: "Submitted work",
    };

    const res = await submitAssignment(1, 10, payload);

    expect(postSpy).toHaveBeenCalled();
    const call = postSpy.mock.calls[0];
    expect(call).toBeDefined();
    expect(call![0]).toBe("/api/v1/courses/workspaces/1/assignments/10/submissions");
    expect(call![1]).toBeInstanceOf(FormData);
    expect((call![1] as FormData).get("submission_type")).toBe("file");
    expect((call![1] as FormData).get("content")).toBe("Submitted work");
    expect(res).toEqual(mockSubmission);
  });

  it("gradeSubmission calls POST with correct endpoint and payload", async () => {
    const mockGrade = {
      id: 5,
      submission_id: 1,
      assignment_id: 10,
      workspace_id: 1,
      student_id: 30,
      grader_id: 10,
      grader_name: "Prof. Alan",
      score: "95.00",
      feedback: "Great work!",
      status: "draft" as const,
      graded_at: "2026-11-10T16:00:00Z",
      released_at: null,
      released_by_id: null,
      created_at: "2026-11-10T16:00:00Z",
      updated_at: "2026-11-10T16:00:00Z",
    };

    const postSpy = vi.spyOn(api, "post").mockResolvedValue({ data: mockGrade });

    const payload = {
      score: 95,
      feedback: "Great work!",
    };

    const res = await gradeSubmission(1, 10, 1, payload);

    expect(postSpy).toHaveBeenCalledWith(
      "/api/v1/courses/workspaces/1/assignments/10/submissions/1/grade",
      payload,
    );
    expect(res).toEqual(mockGrade);
  });

  it("releaseGrades calls POST with correct endpoint and payload", async () => {
    const mockResponse = {
      released_count: 3,
      results: [],
    };

    const postSpy = vi.spyOn(api, "post").mockResolvedValue({ data: mockResponse });

    const res = await releaseGrades(1, 10);

    expect(postSpy).toHaveBeenCalledWith(
      "/api/v1/courses/workspaces/1/assignments/10/release-grades",
      {},
    );
    expect(res).toEqual(mockResponse);
  });
});
