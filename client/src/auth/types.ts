import type { NavGroup } from "../ui/layout/AppShellLayout";

export interface Session {
  user: {
    id: number;
    username: string;
    display_name: string;
    kind: string;
    email: string;
    department: string;
  };
  active_role: string | null;
  roles: string[];
  permissions: string[];
  modules: string[];
  navigation: NavGroup[];
  department_assignments: { department_code: string; department_name: string; role: string; starts_on: string; ends_on: string | null }[];
  department_contexts: { code: string; name: string }[];
  /** Paired with the session cookie. Echoed in X-CSRF-Token on every write. */
  csrf_token: string;
}
