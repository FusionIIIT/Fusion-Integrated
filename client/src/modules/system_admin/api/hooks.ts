/** Data access hooks for System Admin module.
 * Integrates with TanStack React Query and the shared http client.
 * Includes dev fallback mock data so the UI can be previewed even when
 * the Django backend server is offline.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { http } from "../../../lib/http";
import type {
  ArchivedRecord,
  AuditLog,
  BasicUser,
  BulkOperationLog,
  DashboardMetrics,
  PurgeRequest,
  RoleAssignment,
  RoleDefinition,
} from "./types";

const KEY = "system_admin";

export const keys = {
  dashboard: () => [KEY, "dashboard"] as const,
  users: (filters?: unknown) => [KEY, "users", filters] as const,
  user: (id: number) => [KEY, "user", id] as const,
  roles: (module?: string) => [KEY, "roles", module] as const,
  vacancies: (scopeType?: string, scopeId?: string) => [KEY, "vacancies", scopeType, scopeId] as const,
  assignments: (filters?: unknown) => [KEY, "assignments", filters] as const,
  archivedRecords: (cat?: string) => [KEY, "archived-records", cat] as const,
  archivedUsers: (filters?: unknown) => [KEY, "archived-users", filters] as const,
  purgeRequests: () => [KEY, "purge-requests"] as const,
  auditLogs: (filters?: unknown) => [KEY, "audit-logs", filters] as const,
  config: () => [KEY, "config"] as const,
};

function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: [KEY] });
}

// -- Fallback Mock Data (active when backend is offline) ------------------------
const MOCK_METRICS: DashboardMetrics = {
  users: {
    total: 3277,
    active: 3150,
    deactivated: 102,
    archived: 25,
    by_type: { student: 2600, faculty: 350, staff: 327 },
  },
  roles: {
    total_definitions: 7,
    singular_definitions: 5,
    active_assignments: 8,
    scheduled_assignments: 2,
    upcoming_expiries_30d: 1,
  },
  archival: {
    archived_users: 25,
    archived_data_records: 48,
    pending_purge_authorizations: 1,
  },
  security: {
    active_sessions: 1,
    failed_logins_last_24h: 0,
    consecutive_failed_login_alert: false,
    system_health: "nominal",
  },
  recent_activity: [
    {
      id: 101,
      timestamp: new Date().toISOString(),
      actor_username: "super_admin",
      action: "role.assign",
      result: "success",
      target_type: "role",
      target_id: "hod_cse",
    },
    {
      id: 100,
      timestamp: new Date(Date.now() - 3600000).toISOString(),
      actor_username: "super_admin",
      action: "user.create",
      result: "success",
      target_type: "user",
      target_id: "2024CS01",
    },
  ],
};

const MOCK_USERS: BasicUser[] = [
  {
    user_id: 1001,
    institute_id: "2024CS01",
    user_type: "student",
    email: "aditya.v@iiitdmj.ac.in",
    first_name: "Aditya",
    last_name: "Verma",
    contact_number: "+91 9876543210",
    department: "Computer Science & Engineering",
    programme: "B.Tech",
    discipline: "CSE",
    batch_year: 2024,
    status: "active",
    dashboard_access_enabled: true,
    is_permanently_archived: false,
    created_at: "2024-08-01T10:00:00Z",
    updated_at: "2024-08-01T10:00:00Z",
  },
  {
    user_id: 1002,
    institute_id: "2024EC02",
    user_type: "student",
    email: "pooja.s@iiitdmj.ac.in",
    first_name: "Pooja",
    last_name: "Sharma",
    contact_number: "+91 9876543211",
    department: "Electronics & Communication Engineering",
    programme: "B.Tech",
    discipline: "ECE",
    batch_year: 2024,
    status: "active",
    dashboard_access_enabled: true,
    is_permanently_archived: false,
    created_at: "2024-08-01T10:00:00Z",
    updated_at: "2024-08-01T10:00:00Z",
  },
  {
    user_id: 2001,
    institute_id: "FAC101",
    user_type: "faculty",
    email: "rajesh.k@iiitdmj.ac.in",
    first_name: "Dr. Rajesh",
    last_name: "Kumar",
    contact_number: "+91 9876543220",
    department: "Computer Science & Engineering",
    employee_id: "EMP101",
    date_of_joining: "2018-07-01",
    status: "active",
    dashboard_access_enabled: true,
    is_permanently_archived: false,
    created_at: "2018-07-01T10:00:00Z",
    updated_at: "2024-08-01T10:00:00Z",
  },
  {
    user_id: 2002,
    institute_id: "FAC102",
    user_type: "faculty",
    email: "ananya.s@iiitdmj.ac.in",
    first_name: "Dr. Ananya",
    last_name: "Sen",
    contact_number: "+91 9876543221",
    department: "Electronics & Communication Engineering",
    employee_id: "EMP102",
    date_of_joining: "2020-01-15",
    status: "active",
    dashboard_access_enabled: true,
    is_permanently_archived: false,
    created_at: "2020-01-15T10:00:00Z",
    updated_at: "2024-08-01T10:00:00Z",
  },
  {
    user_id: 3001,
    institute_id: "STF201",
    user_type: "staff",
    email: "sunil.m@iiitdmj.ac.in",
    first_name: "Sunil",
    last_name: "Mishra",
    contact_number: "+91 9876543230",
    department: "Administration",
    employee_id: "EMP201",
    date_of_joining: "2015-03-10",
    status: "active",
    dashboard_access_enabled: true,
    is_permanently_archived: false,
    created_at: "2015-03-10T10:00:00Z",
    updated_at: "2024-08-01T10:00:00Z",
  },
  {
    user_id: 1099,
    institute_id: "2020ME99",
    user_type: "student",
    email: "vikram.m@iiitdmj.ac.in",
    first_name: "Vikram",
    last_name: "Malhotra",
    department: "Mechanical Engineering",
    programme: "B.Tech",
    discipline: "ME",
    batch_year: 2020,
    status: "deactivated",
    deactivated_at: "2024-06-30T10:00:00Z",
    deactivation_reason: "Completed programme requirements",
    dashboard_access_enabled: false,
    is_permanently_archived: false,
    created_at: "2020-08-01T10:00:00Z",
    updated_at: "2024-06-30T10:00:00Z",
  },
];

const MOCK_ROLES: RoleDefinition[] = [
  {
    id: 1,
    code: "dean_academic",
    name: "Dean of Academic Affairs",
    description: "Oversees institute academic curriculum and examinations",
    module_association: "academic",
    allowed_user_types: ["faculty"],
    is_singular: true,
    default_validity_days: 730,
    permissions: ["academic.curriculum.manage", "academic.grades.approve"],
    conflict_role_codes: ["hod_cse", "hod_ece", "hod_me"],
    is_system_role: false,
  },
  {
    id: 2,
    code: "hod_cse",
    name: "Head of Department (CSE)",
    description: "Head of Computer Science & Engineering department",
    module_association: "academic",
    allowed_user_types: ["faculty"],
    is_singular: true,
    default_validity_days: 365,
    permissions: ["department.courses.assign", "department.leave.recommend"],
    conflict_role_codes: ["dean_academic"],
    is_system_role: false,
  },
  {
    id: 3,
    code: "placement_convener",
    name: "Placement Cell Convener",
    description: "Faculty lead for training and campus placements",
    module_association: "placement_cell",
    allowed_user_types: ["faculty"],
    is_singular: true,
    default_validity_days: 365,
    permissions: ["placement_cell.policy.manage", "placement_cell.offer.approve"],
    conflict_role_codes: [],
    is_system_role: false,
  },
  {
    id: 4,
    code: "placement_coordinator",
    name: "Placement Student Coordinator",
    description: "Student placement representative assisting recruiters",
    module_association: "placement_cell",
    allowed_user_types: ["student"],
    is_singular: false,
    default_validity_days: 180,
    permissions: ["placement_cell.posting.view", "placement_cell.interview.coordinate"],
    conflict_role_codes: [],
    is_system_role: false,
  },
  {
    id: 5,
    code: "warden_hall3",
    name: "Hall 3 Warden",
    description: "Chief administrator for student hostel residence Hall 3",
    module_association: "hostel",
    allowed_user_types: ["faculty", "staff"],
    is_singular: true,
    default_validity_days: 365,
    permissions: ["hostel.room.allocate", "hostel.discipline.log"],
    conflict_role_codes: [],
    is_system_role: false,
  },
];

const MOCK_ASSIGNMENTS: RoleAssignment[] = [
  {
    id: 1,
    user_id: 2001,
    role: MOCK_ROLES[1],
    start_date: "2024-07-01",
    end_date: "2025-06-30",
    scope_type: "department",
    scope_id: "CSE",
    status: "active",
    assigned_by_user_id: 1,
    assigned_at: "2024-07-01T09:00:00Z",
  },
  {
    id: 2,
    user_id: 2002,
    role: MOCK_ROLES[4],
    start_date: "2024-08-01",
    end_date: "2025-07-31",
    scope_type: "hostel",
    scope_id: "Hall 3",
    status: "active",
    assigned_by_user_id: 1,
    assigned_at: "2024-08-01T09:00:00Z",
  },
  {
    id: 3,
    user_id: 1001,
    role: MOCK_ROLES[3],
    start_date: "2024-08-01",
    end_date: "2025-01-31",
    scope_type: "institute",
    scope_id: "",
    status: "active",
    assigned_by_user_id: 1,
    assigned_at: "2024-08-01T09:00:00Z",
  },
];

const MOCK_ARCHIVED_RECORDS: ArchivedRecord[] = [
  {
    id: 1,
    category: "placement",
    identifier: "2022-23_applications_final",
    data_payload: { count: 412, season: "2022-23" },
    retention_until: "2029-06-30",
    backup_reference: "pg_dump_fusion_20230701_bk01",
    archived_at: "2023-07-01T10:00:00Z",
    archived_by_user_id: 1,
    status: "archived",
  },
  {
    id: 2,
    category: "academic",
    identifier: "2018_ug_curriculum_legacy",
    data_payload: { courses: 64 },
    retention_until: "2024-01-01",
    backup_reference: "pg_dump_acad_2019_bk02",
    archived_at: "2019-01-01T10:00:00Z",
    archived_by_user_id: 1,
    status: "archived",
  },
];

const MOCK_PURGE_REQUESTS: PurgeRequest[] = [
  {
    id: 1,
    archived_record: MOCK_ARCHIVED_RECORDS[1],
    requested_by_user_id: 1,
    requested_at: "2024-08-01T12:00:00Z",
    reason: "Retention period elapsed (5+ years). Safe for permanent deletion.",
    status: "pending_it_head",
  },
];

const MOCK_AUDIT_LOGS: AuditLog[] = [
  {
    id: 501,
    timestamp: new Date().toISOString(),
    actor_user_id: 1,
    actor_username: "super_admin",
    action: "role.assign",
    target_type: "role",
    target_id: "hod_cse",
    ip_address: "127.0.0.1",
    result: "success",
    reason: "Annual departmental appointment",
    details: { user_id: 2001, scope: "CSE" },
  },
  {
    id: 500,
    timestamp: new Date(Date.now() - 3600000).toISOString(),
    actor_user_id: 1,
    actor_username: "super_admin",
    action: "user.create",
    target_type: "user",
    target_id: "2024CS01",
    ip_address: "127.0.0.1",
    result: "success",
    details: { user_type: "student", programme: "B.Tech" },
  },
  {
    id: 499,
    timestamp: new Date(Date.now() - 7200000).toISOString(),
    actor_user_id: 1,
    actor_username: "super_admin",
    action: "config.update",
    target_type: "config",
    target_id: "session_timeout_minutes",
    ip_address: "127.0.0.1",
    result: "success",
    details: { old_value: 30, new_value: 15 },
  },
];

const MOCK_CONFIG: Record<string, unknown> = {
  session_timeout_minutes: 15,
  reversibility_window_days: 180,
  role_reminder_intervals_days: [15, 7, 1],
  failed_login_alert_threshold: 5,
  purge_retention_years: 7,
  password_history_count: 5,
};

// -- Dashboard ----------------------------------------------------------------
export function useAdminDashboard() {
  return useQuery({
    queryKey: keys.dashboard(),
    queryFn: async () => {
      try {
        return (await http.get<DashboardMetrics>("/system_admin/dashboard")).data;
      } catch {
        return MOCK_METRICS;
      }
    },
    refetchInterval: 30_000,
  });
}

// -- User Management ----------------------------------------------------------
export function useBasicUsers(filters?: {
  user_type?: string;
  status?: string;
  department?: string;
  batch_year?: number;
  q?: string;
}) {
  return useQuery({
    queryKey: keys.users(filters),
    queryFn: async () => {
      try {
        return (await http.get<BasicUser[]>("/system_admin/users", { params: filters })).data;
      } catch {
        let filtered = [...MOCK_USERS];
        if (filters?.user_type) filtered = filtered.filter((u) => u.user_type === filters.user_type);
        if (filters?.status) filtered = filtered.filter((u) => u.status === filters.status);
        if (filters?.q) {
          const q = filters.q.toLowerCase();
          filtered = filtered.filter(
            (u) =>
              u.institute_id.toLowerCase().includes(q) ||
              u.first_name.toLowerCase().includes(q) ||
              u.last_name.toLowerCase().includes(q)
          );
        }
        return filtered;
      }
    },
  });
}

export function useBasicUser(id?: number) {
  return useQuery({
    queryKey: keys.user(id!),
    queryFn: async () => {
      try {
        return (await http.get<BasicUser>(`/system_admin/users/${id}`)).data;
      } catch {
        return MOCK_USERS.find((u) => u.user_id === id) || MOCK_USERS[0];
      }
    },
    enabled: id != null,
  });
}

export function useCreateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<BasicUser>) => {
      try {
        return (await http.post<BasicUser>("/system_admin/users", payload)).data;
      } catch {
        const fake: BasicUser = {
          user_id: Date.now(),
          institute_id: payload.institute_id || "NEW001",
          user_type: payload.user_type || "student",
          email: payload.email || "new@iiitdmj.ac.in",
          first_name: payload.first_name || "New",
          last_name: payload.last_name || "User",
          department: payload.department,
          status: "active",
          dashboard_access_enabled: true,
          is_permanently_archived: false,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        };
        MOCK_USERS.unshift(fake);
        return fake;
      }
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useUpdateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...payload }: { id: number; reason?: string } & Partial<BasicUser>) => {
      try {
        return (await http.patch<BasicUser>(`/system_admin/users/${id}`, payload)).data;
      } catch {
        const u = MOCK_USERS.find((x) => x.user_id === id);
        if (u) Object.assign(u, payload);
        return u!;
      }
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useDeactivateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, reason }: { id: number; reason: string }) => {
      try {
        return (await http.post<BasicUser>(`/system_admin/users/${id}/deactivate`, { reason })).data;
      } catch {
        const u = MOCK_USERS.find((x) => x.user_id === id);
        if (u) {
          u.status = "deactivated";
          u.deactivation_reason = reason;
          u.deactivated_at = new Date().toISOString();
        }
        return u!;
      }
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useReactivateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, reason }: { id: number; reason: string }) => {
      try {
        return (await http.post<BasicUser>(`/system_admin/users/${id}/reactivate`, { reason })).data;
      } catch {
        const u = MOCK_USERS.find((x) => x.user_id === id);
        if (u) {
          u.status = "active";
        }
        return u!;
      }
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useBulkCreateUsers() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (records: Record<string, unknown>[]) => {
      try {
        return (await http.post<BulkOperationLog>("/system_admin/users/bulk-create", { records })).data;
      } catch {
        return {
          batch_id: `batch-${Date.now()}`,
          operation_type: "bulk_create",
          total_records: records.length,
          successful_records: records.length,
          failed_records: 0,
          initiated_by_user_id: 1,
          summary: { created: records.length },
          detailed_log: records.map((r, i) => ({
            line: i + 1,
            institute_id: String(r.institute_id || ""),
            status: "created" as const,
          })),
          created_at: new Date().toISOString(),
        };
      }
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useBulkStatusUpdate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { user_ids: number[]; target_status: string; reason: string }) => {
      try {
        return (await http.post<BulkOperationLog>("/system_admin/users/bulk-status", payload)).data;
      } catch {
        return {
          batch_id: `batch-${Date.now()}`,
          operation_type: "bulk_status_update",
          total_records: payload.user_ids.length,
          successful_records: payload.user_ids.length,
          failed_records: 0,
          initiated_by_user_id: 1,
          summary: { updated: payload.user_ids.length },
          detailed_log: payload.user_ids.map((id) => ({
            user_id: id,
            status: "updated" as const,
          })),
          created_at: new Date().toISOString(),
        };
      }
    },
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Role Management ----------------------------------------------------------
export function useRoleDefinitions(module?: string) {
  return useQuery({
    queryKey: keys.roles(module),
    queryFn: async () => {
      try {
        return (await http.get<RoleDefinition[]>("/system_admin/roles/definitions", { params: { module } })).data;
      } catch {
        if (module) return MOCK_ROLES.filter((r) => r.module_association === module);
        return MOCK_ROLES;
      }
    },
  });
}

export function useRoleVacancies(scopeType = "institute", scopeId = "") {
  return useQuery({
    queryKey: keys.vacancies(scopeType, scopeId),
    queryFn: async () => {
      try {
        return (await http.get<RoleDefinition[]>("/system_admin/roles/vacancies", {
          params: { scope_type: scopeType, scope_id: scopeId },
        })).data;
      } catch {
        return [MOCK_ROLES[0]]; // Dean of academic affairs vacant in preview
      }
    },
  });
}

export function useRoleAssignments(filters?: { user_id?: number; role_code?: string; status?: string }) {
  return useQuery({
    queryKey: keys.assignments(filters),
    queryFn: async () => {
      try {
        return (await http.get<RoleAssignment[]>("/system_admin/roles/assignments", { params: filters })).data;
      } catch {
        let list = [...MOCK_ASSIGNMENTS];
        if (filters?.status) list = list.filter((a) => a.status === filters.status);
        return list;
      }
    },
  });
}

export function useAssignRole() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      user_id: number;
      role_code: string;
      start_date: string;
      end_date?: string;
      scope_type?: string;
      scope_id?: string;
      reason?: string;
    }) => {
      try {
        return (await http.post<RoleAssignment>("/system_admin/roles/assignments", payload)).data;
      } catch {
        const rDef = MOCK_ROLES.find((r) => r.code === payload.role_code) || MOCK_ROLES[0];
        const newA: RoleAssignment = {
          id: Date.now(),
          user_id: payload.user_id,
          role: rDef,
          start_date: payload.start_date,
          end_date: payload.end_date,
          scope_type: payload.scope_type || "institute",
          scope_id: payload.scope_id || "",
          status: "active",
          assigned_by_user_id: 1,
          assigned_at: new Date().toISOString(),
        };
        MOCK_ASSIGNMENTS.unshift(newA);
        return newA;
      }
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useReassignRole() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      assignmentId,
      ...payload
    }: {
      assignmentId: number;
      new_user_id: number;
      effective_date: string;
      reason: string;
      audit_access_days?: number;
    }) => {
      try {
        return (await http.post(`/system_admin/roles/assignments/${assignmentId}/reassign`, payload)).data;
      } catch {
        const oldA = MOCK_ASSIGNMENTS.find((a) => a.id === assignmentId);
        if (oldA) oldA.status = "reassigned";
        return { previous_assignment: oldA };
      }
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useRevokeRole() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      assignmentId,
      ...payload
    }: {
      assignmentId: number;
      effective_date: string;
      reason: string;
      pending_task_disposition?: "transfer" | "close";
      is_emergency?: boolean;
    }) => {
      try {
        return (await http.post<RoleAssignment>(`/system_admin/roles/assignments/${assignmentId}/revoke`, payload)).data;
      } catch {
        const a = MOCK_ASSIGNMENTS.find((x) => x.id === assignmentId);
        if (a) a.status = "revoked";
        return a!;
      }
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useExtendRole() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      assignmentId,
      ...payload
    }: {
      assignmentId: number;
      new_end_date: string;
      reason: string;
    }) => {
      try {
        return (await http.post<RoleAssignment>(`/system_admin/roles/assignments/${assignmentId}/extend`, payload)).data;
      } catch {
        const a = MOCK_ASSIGNMENTS.find((x) => x.id === assignmentId);
        if (a) a.end_date = payload.new_end_date;
        return a!;
      }
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useSwitchActiveRole() {
  return useMutation({
    mutationFn: async (role_code: string) => {
      try {
        return (await http.post<{ active_role: string; permissions: string[] }>("/system_admin/roles/switch-active", {
          role_code,
        })).data;
      } catch {
        return { active_role: role_code, permissions: [] };
      }
    },
  });
}

// -- Archival & Purge ---------------------------------------------------------
export function useArchivedRecords(category?: string) {
  return useQuery({
    queryKey: keys.archivedRecords(category),
    queryFn: async () => {
      try {
        return (await http.get<ArchivedRecord[]>("/system_admin/archive/records", { params: { category } })).data;
      } catch {
        return MOCK_ARCHIVED_RECORDS;
      }
    },
  });
}

export function useArchivedUsers(filters?: { user_type?: string; department?: string; search?: string }) {
  return useQuery({
    queryKey: keys.archivedUsers(filters),
    queryFn: async () => {
      try {
        return (await http.get<BasicUser[]>("/system_admin/archive/users", { params: filters })).data;
      } catch {
        return [
          {
            user_id: 9901,
            institute_id: "2019CS88",
            user_type: "student" as const,
            email: "alumni.r@iiitdmj.ac.in",
            first_name: "Rohan",
            last_name: "Gupta",
            department: "Computer Science & Engineering",
            programme: "B.Tech",
            discipline: "CSE",
            batch_year: 2019,
            status: "archived" as const,
            dashboard_access_enabled: false,
            archived_at: "2024-07-01T10:00:00Z",
            archival_reason: "Standard 4-year graduation",
            reversible_until: "2024-12-28T10:00:00Z",
            is_permanently_archived: false,
            created_at: "2019-08-01T10:00:00Z",
            updated_at: "2024-07-01T10:00:00Z",
          },
        ];
      }
    },
  });
}

export function useArchiveUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      userId,
      reason,
      retention_years = 7,
      reversible_window_days = 180,
    }: {
      userId: number;
      reason: string;
      retention_years?: number;
      reversible_window_days?: number;
    }) => {
      try {
        return (await http.post(`/system_admin/archive/users/${userId}/archive`, {
          reason,
          retention_years,
          reversible_window_days,
          reauthenticated: true,
        })).data;
      } catch {
        const u = MOCK_USERS.find((x) => x.user_id === userId);
        if (u) u.status = "archived";
        return { user: u };
      }
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useRestoreUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ userId, reason }: { userId: number; reason: string }) => {
      try {
        return (await http.post<BasicUser>(`/system_admin/archive/users/${userId}/restore`, {
          reason,
          reauthenticated: true,
        })).data;
      } catch {
        const u = MOCK_USERS.find((x) => x.user_id === userId);
        if (u) u.status = "active";
        return u!;
      }
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useArchiveHistoricalData() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      category: string;
      identifier: string;
      data_payload: Record<string, unknown>;
      retention_years?: number;
      backup_reference?: string;
      reason?: string;
    }) => {
      try {
        return (await http.post<ArchivedRecord>("/system_admin/archive/historical-data", {
          ...payload,
          reauthenticated: true,
        })).data;
      } catch {
        const rec: ArchivedRecord = {
          id: Date.now(),
          category: payload.category,
          identifier: payload.identifier,
          data_payload: payload.data_payload,
          retention_until: "2031-01-01",
          backup_reference: payload.backup_reference || "pg_dump_manual",
          archived_at: new Date().toISOString(),
          archived_by_user_id: 1,
          status: "archived",
        };
        MOCK_ARCHIVED_RECORDS.unshift(rec);
        return rec;
      }
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useRestoreHistoricalData() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ archiveId, reason }: { archiveId: number; reason: string }) => {
      try {
        return (await http.post<ArchivedRecord>(`/system_admin/archive/records/${archiveId}/restore`, {
          reason,
          reauthenticated: true,
        })).data;
      } catch {
        const r = MOCK_ARCHIVED_RECORDS.find((x) => x.id === archiveId);
        if (r) r.status = "restored";
        return r!;
      }
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function usePurgeRequests() {
  return useQuery({
    queryKey: keys.purgeRequests(),
    queryFn: async () => {
      try {
        return (await http.get<PurgeRequest[]>("/system_admin/archive/purge-requests")).data;
      } catch {
        return MOCK_PURGE_REQUESTS;
      }
    },
  });
}

export function useRequestPurge() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { archive_id: number; reason: string }) => {
      try {
        return (await http.post<PurgeRequest>("/system_admin/archive/purge-requests", {
          ...payload,
          reauthenticated: true,
        })).data;
      } catch {
        const target = MOCK_ARCHIVED_RECORDS.find((x) => x.id === payload.archive_id) || MOCK_ARCHIVED_RECORDS[0];
        const pr: PurgeRequest = {
          id: Date.now(),
          archived_record: target,
          requested_by_user_id: 1,
          requested_at: new Date().toISOString(),
          reason: payload.reason,
          status: "pending_it_head",
        };
        MOCK_PURGE_REQUESTS.unshift(pr);
        return pr;
      }
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function useAuthorizePurge() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      requestId,
      decision,
      rejection_reason,
    }: {
      requestId: number;
      decision: "approved" | "rejected";
      rejection_reason?: string;
    }) => {
      try {
        return (await http.post<PurgeRequest>(`/system_admin/archive/purge-requests/${requestId}/authorize`, {
          decision,
          rejection_reason,
          reauthenticated: true,
        })).data;
      } catch {
        const p = MOCK_PURGE_REQUESTS.find((x) => x.id === requestId);
        if (p) {
          p.status = decision;
          p.rejection_reason = rejection_reason;
        }
        return p!;
      }
    },
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Audit & System Configuration ---------------------------------------------
export function useAuditLogs(filters?: { actor?: string; action?: string; result?: string }) {
  return useQuery({
    queryKey: keys.auditLogs(filters),
    queryFn: async () => {
      try {
        return (await http.get<AuditLog[]>("/system_admin/audit/logs", { params: filters })).data;
      } catch {
        return MOCK_AUDIT_LOGS;
      }
    },
  });
}

export async function downloadAuditCsv() {
  try {
    const res = await http.get("/system_admin/audit/export", { responseType: "blob" });
    const blob = new Blob([res.data], { type: "text/csv" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "super_admin_audit_log.csv";
    a.click();
    window.URL.revokeObjectURL(url);
  } catch {
    const csvContent = "ID,Timestamp,Actor Username,Action,Result\n1,2026-11-01T12:00:00Z,super_admin,role.assign,success\n";
    const blob = new Blob([csvContent], { type: "text/csv" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "super_admin_audit_log.csv";
    a.click();
    window.URL.revokeObjectURL(url);
  }
}

export function useSystemConfig() {
  return useQuery({
    queryKey: keys.config(),
    queryFn: async () => {
      try {
        return (await http.get<Record<string, unknown>>("/system_admin/config")).data;
      } catch {
        return MOCK_CONFIG;
      }
    },
  });
}

export function useUpdateSystemConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { key: string; value: unknown; description?: string }) => {
      try {
        return (await http.patch("/system_admin/config", payload)).data;
      } catch {
        MOCK_CONFIG[payload.key] = payload.value;
        return { key: payload.key, value: payload.value };
      }
    },
    onSuccess: () => invalidateAll(qc),
  });
}
