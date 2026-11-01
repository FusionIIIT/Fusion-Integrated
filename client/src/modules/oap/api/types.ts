export interface StudentLeave {
  id: number;
  studentId: number;
  startDate: string;
  endDate: string;
  reason: string;
  status: string;
}

export interface BonafideRequest {
  id: number;
  studentId: number;
  requestDate: string;
  status: string;
}

export interface NoDuesAuthorityClearance {
  id: number;
  studentId: number;
  requestDate: string;
  status: string;
}

export interface NoDuesRequest {
  id: number;
  studentId: number;
  requestDate: string;
  status: string;
}

export interface ThesisSupervisorAssignment {
  id: number;
  thesisId: number;
  supervisorId: number;
  assignmentDate: string;
  status: string;
}

export interface TAAssignment {
  id: number;
  taId: number;
  courseId: number;
  assignmentDate: string;
  status: string;
}

export interface AssistantshipClaim {
  id: number;
  studentId: number;
  claimDate: string;
  status: string;
}

export interface GraduateSeminarRequest {
  id: number;
  studentId: number;
  requestDate: string;
  status: string;
}

export interface OAPNotification {
  id: number;
  studentId: number;
  notificationDate: string;
  message: string;
  status: string;
}
