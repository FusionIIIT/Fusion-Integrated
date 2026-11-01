import axiosInstance from "../context/axiosInstance";

const BASE = "/archive";

export const fetchArchiveList = async (type, status, filters = {}) => {
  const { data } = await axiosInstance.get(`${BASE}/list/`, { params: { type, status, ...filters } });
  return data;
};

export const archiveUsers = async (usernames, type, action) => {
  const { data } = await axiosInstance.post(`${BASE}/action/`, { usernames, type, action });
  return data;
};

export const restoreUsers = async (usernames, type) => {
  const { data } = await axiosInstance.post(`${BASE}/restore/`, { usernames, type });
  return data;
};
