// client/src/modules/elm/api/types.ts

export interface LeaveCategory {
  id: number;
  name: string;
  description: string;
}

export interface LeaveApplicationStatus {
  id: number;
  name: string;
  description: string;
}

export interface LeaveBalance {
  employeeId: number;
  leaveCategoryId: number;
  balance: number;
  leaveCategory: LeaveCategory;
}

export interface LeaveApplication {
  id: number;
  employeeId: number;
  leaveCategoryId: number;
  startDate: Date;
  endDate: Date;
  reason: string;
  statusId: number;
  leaveCategory: LeaveCategory;
  status: LeaveApplicationStatus;
}

export interface SubstituteAssignment {
  id: number;
  employeeId: number;
  substituteId: number;
  leaveCategoryId: number;
  startDate: Date;
  endDate: Date;
  leaveCategory: LeaveCategory;
}

export interface ApprovalHistory {
  id: number;
  leaveApplicationId: number;
  approverId: number;
  action: string;
  actionDate: Date;
  comments: string;
  leaveApplication: LeaveApplication;
}

export interface LeaveCancellation {
  id: number;
  leaveApplicationId: number;
  cancelledById: number;
  cancellationDate: Date;
  reason: string;
  leaveApplication: LeaveApplication;
}

export interface LeaveExtension {
  id: number;
  leaveApplicationId: number;
  extensionById: number;
  extensionDate: Date;
  reason: string;
  leaveApplication: LeaveApplication;
}

export interface LeaveResumption {
  id: number;
  leaveApplicationId: number;
  resumptionById: number;
  resumptionDate: Date;
  reason: string;
  leaveApplication: LeaveApplication;
}