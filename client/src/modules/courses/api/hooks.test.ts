import { describe, expect, it, vi } from "vitest";

import { api } from "../../../lib/api";
import { updateWorkspace } from "./hooks";

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
});
