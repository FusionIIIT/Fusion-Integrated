import { http } from "@/lib/http";
import type { Complaint, InventoryItem } from "./types";

export const iwdApi = {
  listComplaints: () => http.get<Complaint[]>("/api/v1/iwd/complaints"),
  getComplaint: (id: number) => http.get<Complaint>(`/api/v1/iwd/complaints/${id}`),
  createComplaint: (data: {
    category: "civil" | "electrical";
    location: string;
    urgency: "low" | "medium" | "high" | "emergency";
    remarks?: string;
  }) => http.post<Complaint>("/api/v1/iwd/complaints", data),
  listInventory: () => http.get<InventoryItem[]>("/api/v1/iwd/inventory"),
};
