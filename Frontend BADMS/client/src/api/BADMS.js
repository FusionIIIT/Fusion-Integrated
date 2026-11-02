import axiosInstance from "../context/axiosInstance";

// BADMS endpoints are grouped under /badms/. The backend must enforce RBAC and
// determine the next workflow stage; the frontend never grants approvals itself.
const BASE = "/badms";

const unwrap = (response) => response.data;

export const fetchArchiveRequests = async () =>
  unwrap(await axiosInstance.get(`${BASE}/archive-requests/`));

export const createArchiveRequest = async (payload) => {
  const body = new FormData();
  Object.entries(payload).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== "") body.append(key, value);
  });
  return unwrap(await axiosInstance.post(`${BASE}/archive-requests/`, body));
};

export const fetchRestoreRequests = async () =>
  unwrap(await axiosInstance.get(`${BASE}/restore-requests/`));

export const createRestoreRequest = async (payload) =>
  unwrap(await axiosInstance.post(`${BASE}/restore-requests/`, payload));

export const fetchApprovalQueue = async () =>
  unwrap(await axiosInstance.get(`${BASE}/approval-queue/`));

export const decideApproval = async (requestId, payload) =>
  unwrap(await axiosInstance.post(`${BASE}/approval-queue/${requestId}/decision/`, payload));

export const fetchStorageRequests = async () =>
  unwrap(await axiosInstance.get(`${BASE}/storage-requests/`));

export const createStorageRequest = async (payload) =>
  unwrap(await axiosInstance.post(`${BASE}/storage-requests/`, payload));

export const fetchSecurityStatus = async () =>
  unwrap(await axiosInstance.get(`${BASE}/security/status/`));

export const fetchSecurityAuditLogs = async () =>
  unwrap(await axiosInstance.get(`${BASE}/security/audit-logs/`));

export const fetchFailureAlerts = async () =>
  unwrap(await axiosInstance.get(`${BASE}/failure-alerts/`));
