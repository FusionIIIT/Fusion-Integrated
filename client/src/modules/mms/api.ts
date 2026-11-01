import axios from "axios";
import {
  DailyMenuItem,
  MessFeedback,
  MessRegistration,
  MessRoleAssignment,
  RebateRequest,
  RegistrationWindow,
} from "./types";

const client = axios.create({
  baseURL: "/api/v1/mms",
  headers: {
    "Content-Type": "application/json",
  },
});

export const fetchActiveRoles = async (): Promise<MessRoleAssignment[]> => {
  const res = await client.get<MessRoleAssignment[]>("/roles/");
  return res.data;
};

export const assignMessRole = async (data: {
  employee_id: number;
  role: string;
  start_date: string;
  end_date?: string | null;
  remarks?: string;
}): Promise<MessRoleAssignment> => {
  const res = await client.post<MessRoleAssignment>("/roles/", data);
  return res.data;
};

export const fetchCurrentWindow = async (
  messName: string = "Central Mess",
): Promise<RegistrationWindow> => {
  const res = await client.get<RegistrationWindow>(`/window/?mess_name=${encodeURIComponent(messName)}`);
  return res.data;
};

export const openRegistrationWindow = async (data: {
  name: string;
  mess_name?: string;
  start_date: string;
  end_date: string;
}): Promise<RegistrationWindow> => {
  const res = await client.post<RegistrationWindow>("/window/", data);
  return res.data;
};

export const fetchMyRegistration = async (): Promise<MessRegistration> => {
  const res = await client.get<MessRegistration>("/registration/mine/");
  return res.data;
};

export const submitRegistration = async (data: {
  start_date: string;
  end_date?: string | null;
  mess_name?: string;
  remarks?: string;
}): Promise<MessRegistration> => {
  const res = await client.post<MessRegistration>("/registration/submit/", data);
  return res.data;
};

export const submitDeregistration = async (
  registrationId: number,
  data: { reason: string },
): Promise<MessRegistration> => {
  const res = await client.post<MessRegistration>(
    `/registration/${registrationId}/deregister/`,
    data,
  );
  return res.data;
};

export const fetchPendingRegistrations = async (): Promise<MessRegistration[]> => {
  const res = await client.get<MessRegistration[]>("/registrations/?status=PENDING");
  return res.data;
};

export const reviewRegistration = async (
  registrationId: number,
  data: { approve: boolean; remarks?: string },
): Promise<MessRegistration> => {
  const res = await client.post<MessRegistration>(
    `/registrations/${registrationId}/review/`,
    data,
  );
  return res.data;
};

export const fetchWeeklyMenu = async (
  messName: string = "Central Mess",
): Promise<DailyMenuItem[]> => {
  const res = await client.get<DailyMenuItem[]>(`/menu/?mess_name=${encodeURIComponent(messName)}`);
  return res.data;
};

export const updateMenuItem = async (data: {
  day_of_week: string;
  meal_time: string;
  items: string;
  mess_name?: string;
}): Promise<DailyMenuItem> => {
  const res = await client.post<DailyMenuItem>("/menu/", data);
  return res.data;
};

export const fetchMyRebates = async (): Promise<RebateRequest[]> => {
  const res = await client.get<RebateRequest[]>("/rebates/mine/");
  return res.data;
};

export const submitRebate = async (data: {
  start_date: string;
  end_date: string;
  reason: string;
  mess_name?: string;
}): Promise<RebateRequest> => {
  const res = await client.post<RebateRequest>("/rebates/apply/", data);
  return res.data;
};

export const fetchPendingRebates = async (): Promise<RebateRequest[]> => {
  const res = await client.get<RebateRequest[]>("/rebates/?status=PENDING");
  return res.data;
};

export const reviewRebate = async (
  rebateId: number,
  data: {
    approve: boolean;
    approved_start_date?: string | null;
    approved_end_date?: string | null;
    remarks?: string;
  },
): Promise<RebateRequest> => {
  const res = await client.post<RebateRequest>(`/rebates/${rebateId}/review/`, data);
  return res.data;
};

export const submitFeedback = async (data: {
  rating: number;
  category: string;
  comments: string;
  mess_name?: string;
}): Promise<MessFeedback> => {
  const res = await client.post<MessFeedback>("/feedback/", data);
  return res.data;
};
