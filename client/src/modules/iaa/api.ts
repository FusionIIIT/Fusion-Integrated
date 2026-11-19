import { http } from "../../lib/http";

export const activeRoleKey = "iaa.activeRole";
export const activeRole = () => sessionStorage.getItem(activeRoleKey) ?? "";

http.interceptors.request.use((config) => {
  if (config.url?.startsWith("/iaa")) {
    const role = activeRole();
    if (role) config.headers.set("X-IAA-Active-Role", role);
  }
  return config;
});

export interface IaaRecord {
  id: number;
  status: string;
  department: string;
  description?: string;
  purpose?: string;
  amount?: string;
  claimed_amount?: string;
  request_type?: string;
  created_at: string;
}

export interface IaaNotification {
  id: number;
  title: string;
  message: string;
  event: string;
  created_at: string;
  read_at: string | null;
}

export async function getActiveRoles() {
  return (await http.get<{ roles: string[]; active_role: string | null }>(
    "/iaa/roles/active")).data;
}

export async function setActiveRole(role: string) {
  await http.post("/iaa/roles/active", { active_role: role });
  sessionStorage.setItem(activeRoleKey, role);
}

export async function list<T>(path: string) {
  return (await http.get<{ results: T[] }>(path)).data.results;
}
