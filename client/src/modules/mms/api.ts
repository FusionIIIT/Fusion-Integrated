import { http } from "../../lib/http";
import type {
  DailyMenuItem,
  MessFeedback,
  MessRegistration,
  RebateRequest,
  RegistrationWindow,
} from "./types";

export const getWeeklyMenu = async (messName = "Central Mess"): Promise<DailyMenuItem[]> => {
  const res = await http.get<{ results: DailyMenuItem[] }>(`/mms/menu/?mess_name=${encodeURIComponent(messName)}`);
  return res.data.results;
};

export const getRegistrationWindows = async (): Promise<RegistrationWindow[]> => {
  const res = await http.get<{ results: RegistrationWindow[] }>("/mms/windows/");
  return res.data.results;
};

export const getStudentRegistrations = async (): Promise<MessRegistration[]> => {
  const res = await http.get<{ results: MessRegistration[] }>("/mms/registrations/");
  return res.data.results;
};

export const submitRegistration = async (windowId: number, messName: string): Promise<MessRegistration> => {
  const res = await http.post<MessRegistration>("/mms/registrations/", {
    window_id: windowId,
    mess_name: messName,
  });
  return res.data;
};

export const getRebates = async (): Promise<RebateRequest[]> => {
  const res = await http.get<{ results: RebateRequest[] }>("/mms/rebates/");
  return res.data.results;
};

export const submitRebate = async (data: {
  mess_name: string;
  start_date: string;
  end_date: string;
  reason: string;
}): Promise<RebateRequest> => {
  const res = await http.post<RebateRequest>("/mms/rebates/", data);
  return res.data;
};

export const submitFeedback = async (data: {
  mess_name: string;
  category: string;
  comment: string;
}): Promise<MessFeedback> => {
  const res = await http.post<MessFeedback>("/mms/feedback/", data);
  return res.data;
};

