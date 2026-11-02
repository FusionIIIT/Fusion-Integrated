import axiosInstance from "../context/axiosInstance";

// BADMS workflow API contract. These endpoints must be implemented/exposed by
// the backend team; the existing project currently exposes backup/archive APIs
// but not all approval, storage-request and security-audit endpoints.
const BASE = "/badms";

export const fetchArchiveRequests = async () => {
  const { data } = await axiosInstance.get(`${BASE}/archive-requests/`);
  return data;
};

export const createArchiveRequest = async (payload) => {
  const { data } = await axiosInstance.post(`${BASE}/archive-requests/`, payload);
  return data;
};

export const fetchRestoreRequests = async () => {
  const { data } = await axiosInstance.get(`${BASE}/restore-requests/`);
  return data;
};

export const createRestoreRequest = async (payload) => {
  const { data } = await axiosInstance.post(`${BASE}/restore-requests/`, payload);
  return data;
};

export const fetchApprovalQueue = async (status = "pending") => {
  const { data } = await axiosInstance.get(`${BASE}/approvals/`, { params: { status } });
  return data;
};

export const decideApproval = async (requestId, decision, comments = "") => {
  const { data } = await axiosInstance.patch(
    `${BASE}/approvals/${requestId}/decision/`,
    { decision, comments },
  );
  return data;
};

export const fetchStorageRequests = async () => {
  const { data } = await axiosInstance.get(`${BASE}/storage-requests/`);
  return data;
};

export const createStorageRequest = async (payload) => {
  const { data } = await axiosInstance.post(`${BASE}/storage-requests/`, payload);
  return data;
};

export const fetchSecurityStatus = async () => {
  const { data } = await axiosInstance.get(`${BASE}/security/status/`);
  return data;
};

export const fetchSecurityAuditLogs = async () => {
  const { data } = await axiosInstance.get(`${BASE}/security/audit-logs/`);
  return data;
};
