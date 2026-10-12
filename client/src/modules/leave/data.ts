export type LeaveBalance = {
  code: string;
  label: string;
  used: number;
  available: number;
  entitled: number;
  carry_forward: number;
};

export type LeaveRequest = {
  id: string;
  leave_type: string;
  start_date: string;
  end_date: string;
  days_requested: number;
  purpose: string;
  status: string;
  substitute: string;
};

export const leaveBalances: LeaveBalance[] = [
  { code: "CL", label: "Casual Leave", used: 1.5, available: 6.5, entitled: 8, carry_forward: 0 },
  { code: "RH", label: "Restricted Holiday", used: 0, available: 2, entitled: 2, carry_forward: 0 },
  { code: "SCL", label: "Special Casual Leave", used: 1, available: 14, entitled: 15, carry_forward: 0 },
  { code: "EL", label: "Earned Leave", used: 2, available: 12, entitled: 14, carry_forward: 0 },
  { code: "COL", label: "Compensatory / Medical Leave", used: 3, available: 17, entitled: 20, carry_forward: 0 },
  { code: "VL", label: "Vacation Leave", used: 5, available: 55, entitled: 60, carry_forward: 0 },
];

export const leaveRequests: LeaveRequest[] = [
  {
    id: "EL-2025-001",
    leave_type: "EL",
    start_date: "2025-07-12",
    end_date: "2025-07-15",
    days_requested: 4,
    purpose: "Family obligation",
    status: "approved",
    substitute: "Arjun Nair",
  },
  {
    id: "CL-2025-003",
    leave_type: "CL",
    start_date: "2025-08-01",
    end_date: "2025-08-01",
    days_requested: 0.5,
    purpose: "Personal appointment",
    status: "pending",
    substitute: "Ananya Singh",
  },
  {
    id: "RH-2025-002",
    leave_type: "RH",
    start_date: "2025-06-18",
    end_date: "2025-06-18",
    days_requested: 1,
    purpose: "Religious observance",
    status: "approved",
    substitute: "Sidharth Rao",
  },
];

export const reviewItems = [
  {
    id: "CL-2025-005",
    employee: "Ritika Sharma",
    leave_type: "CL",
    start_date: "2025-08-06",
    end_date: "2025-08-08",
    days_requested: 3,
    status: "pending",
    substitute: "Vikas Mehta",
    purpose: "Travel and family visit",
  },
  {
    id: "EL-2025-010",
    employee: "Karan Verma",
    leave_type: "EL",
    start_date: "2025-08-20",
    end_date: "2025-08-25",
    days_requested: 6,
    status: "recommended",
    substitute: "Meera Joshi",
    purpose: "Outstation leave",
  },
];

export const leaveTypes = [
  { code: "CL", label: "Casual Leave", annual_limit: 8, half_day_supported: true },
  { code: "RH", label: "Restricted Holiday", annual_limit: 2, half_day_supported: false },
  { code: "SCL", label: "Special Casual Leave", annual_limit: 15, half_day_supported: true },
  { code: "EL", label: "Earned Leave", annual_limit: 30, half_day_supported: true },
  { code: "COL", label: "Compensatory / Medical Leave", annual_limit: 20, half_day_supported: true },
  { code: "VL", label: "Vacation Leave", annual_limit: 60, half_day_supported: true },
];
