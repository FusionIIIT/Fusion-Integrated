import { useQuery } from "@tanstack/react-query";

import { useAuth } from "../../../auth/AuthProvider";
import { http } from "../../../lib/http";

export interface Acting {
  role: "student" | "faculty" | "hod" | "dept_admin" | "central" | null;
  department: string | null;
}

// The IAM sends every held role's permissions, so each office control also needs the acting role.
const OWNERS: Record<string, Acting["role"][]> = {
  "department.department.update": ["dept_admin"],
  "department.official_change.view": ["dept_admin", "hod"],
  "department.official_change.create": ["dept_admin"],
  "department.official_change.approve": ["hod"],
  "department.announcement.create": ["faculty", "dept_admin", "hod"],
  "department.announcement.update": ["hod"],
  "department.announcement.delete": ["hod"],
  "department.inventory_item.create": ["dept_admin"],
  "department.stock_movement.view": ["dept_admin", "hod"],
  "department.stock_request.create": ["faculty"],
  "department.stock_request.approve": ["hod"],
  "department.stock_issue.create": ["dept_admin"],
  "department.feedback.create": ["student", "faculty"],
  "department.feedback.review": ["dept_admin"],
  "department.feedback_resolution.create": ["dept_admin", "hod"],
  "department.timetable.create": ["dept_admin"],
  "department.timetable.update": ["dept_admin"],
  "department.lab_resource.update": ["dept_admin"],
  "department.profile.update": ["dept_admin"],
  "department.role_assignment.assign": ["central"],
};

export function useActing() {
  return useQuery({
    queryKey: ["department", "context"],
    queryFn: async () => (await http.get<Acting>("/department/context")).data,
  });
}

// can(permission) for a control: the permission, held while acting in a role that owns it.
export function useCanAct(): (permission: string) => boolean {
  const { can } = useAuth();
  const role = useActing().data?.role ?? null;
  return (permission) => can(permission) && (OWNERS[permission]?.includes(role) ?? true);
}
