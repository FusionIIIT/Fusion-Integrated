import { http } from "../../../lib/http";
import type {
  EmployeeLeaveBalance,
  LeaveApplication,
  LeaveCategory,
  SubmitLeaveApplicationDTO,
} from "./types";

const ROOT = "/elm";

export async function getLeaveCategories(): Promise<LeaveCategory[]> {
  return (await http.get<LeaveCategory[]>(`${ROOT}/categories`)).data;
}

export async function getApplications(): Promise<LeaveApplication[]> {
  return (await http.get<LeaveApplication[]>(`${ROOT}/applications`)).data;
}

export async function getApplication(id: number): Promise<LeaveApplication> {
  return (await http.get<LeaveApplication>(`${ROOT}/applications/${id}`)).data;
}

export async function submitLeaveApplication(
  dto: SubmitLeaveApplicationDTO,
): Promise<LeaveApplication> {
  return (await http.post<LeaveApplication>(`${ROOT}/applications`, dto)).data;
}

export async function withdrawApplication(id: number): Promise<LeaveApplication> {
  return (await http.post<LeaveApplication>(
    `${ROOT}/applications/${id}/withdraw`, {},
  )).data;
}

export async function getEmployeeBalance(): Promise<EmployeeLeaveBalance[]> {
  const response = await http.get<{
    user_id: number;
    balances: Record<string, EmployeeLeaveBalance>;
  }>(`${ROOT}/balance`);
  return Object.values(response.data.balances);
}
