import type { Session as User } from "../../../auth/types";

export interface LeaveCategory {
  id: number;
  name: string;
  description?: string;
}

export interface LeaveRequest {
  id: number;
  user: User;
  leaveType: string;
  startDate: Date;
  endDate: Date;
  reason: string;
  status: 'pending' | 'approved' | 'cancelled' | 'withdrawn' | 'resumed' | 'extended';
  approvedBy?: User;
  cancelledBy?: User;
  resumedBy?: User;
  extendedBy?: User;
}

export interface LeaveRequestForm {
  leaveType: string;
  startDate: Date;
  endDate: Date;
  reason: string;
  substituteId?: number; // Nullable for non-substitute requests
}

export interface LeaveSummary {
  totalPending: number;
  totalApproved: number;
  totalCancelled: number;
  totalWithdrawn: number;
  totalResumed: number;
  totalExtended: number;
}
