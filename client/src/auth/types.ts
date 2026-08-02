import type { NavGroup } from "../ui/layout/AppShellLayout";

export interface Session {
  user: {
    id: number;
    username: string;
    display_name: string;
    kind: string;
    email: string;
  };
  active_role: string | null;
  roles: string[];
  permissions: string[];
  modules: string[];
  navigation: NavGroup[];
  /** Paired with the session cookie. Echoed in X-CSRF-Token on every write. */
  csrf_token: string;
}
