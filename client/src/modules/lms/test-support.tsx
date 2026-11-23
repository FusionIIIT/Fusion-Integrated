import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import { AuthProvider } from "../../auth/AuthProvider";
import { RequirePermission } from "../../auth/RequirePermission";
import type { Session } from "../../auth/types";
import { http } from "../../lib/http";
import type { Course } from "./api/types";

export const course: Course = {
  id: 1, external_offering_key: `cof_${"a".repeat(64)}`, course_code: "SYN101", course_name: "Synthetic Course",
  working_year: "2026", session: "Autumn", syllabus: "Published syllabus", schedule: "Monday",
  details_published_at: "2026-01-01T00:00:00Z", acting_course_role: "FACULTY",
  can_post_announcements: true, staff: [], sections: [],
};
export const pageOf = <T,>(results: T[]) => ({ results, next: null, previous: null });

export function mockReads(overrides: Record<string, unknown> = {}, errors: Record<string, unknown> = {}) {
  const values: Record<string, unknown> = {
    "/lms/courses/": pageOf([course]), "/lms/courses/1/": course,
    "/lms/courses/1/policy/": { version: 1, can_ta_post_announcements: false },
    "/lms/courses/1/materials/": pageOf([]), "/lms/courses/1/announcements/": pageOf([]),
    "/lms/courses/1/assignments/": pageOf([]), "/lms/courses/1/grades/": pageOf([]), ...overrides,
  };
  return vi.spyOn(http, "get").mockImplementation(async (url) => {
    if (String(url) in errors) throw errors[String(url)];
    return { data: values[String(url)] };
  });
}

export function renderLms(node: ReactNode, permissions: string[], guard?: string, activeRole = "faculty") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  const session: Session = { user: { id: 1, username: "synthetic", display_name: "Synthetic User", kind: "faculty", email: "" },
    active_role: activeRole, roles: [activeRole], permissions, modules: ["lms"], navigation: [], csrf_token: "fixture" };
  client.setQueryData(["session"], session);
  return render(<MemoryRouter><QueryClientProvider client={client}><MantineProvider><AuthProvider>
    {guard ? <RequirePermission permission={guard}>{node}</RequirePermission> : node}
  </AuthProvider></MantineProvider></QueryClientProvider></MemoryRouter>);
}

export async function chooseCourse() {
  fireEvent.change(await screen.findByLabelText("Course"), { target: { value: "1" } });
}

export const facultyPermissions = ["course.view", "course.update", "course_policy.update", "course_policy.view",
  "section.create", "section.update", "material.create", "material.update", "material.publish",
  "material.view", "assignment.view", "assignment.create", "assignment.update", "assignment.publish",
  "announcement.view", "announcement.create", "submission.view", "grade.view", "grade.create", "grade.update", "grade.publish"].map((code) => `lms.${code}`);
