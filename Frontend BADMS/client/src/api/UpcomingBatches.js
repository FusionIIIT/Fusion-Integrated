import axiosInstance from "../context/axiosInstance";

const BASE = "/upcoming-batches";

export const fetchBatches = async () => {
  const { data } = await axiosInstance.get(`${BASE}/sync/`);
  return data;
};

export const fetchDisciplines = async () => {
  const { data } = await axiosInstance.get(`${BASE}/disciplines/`);
  return data.disciplines || [];
};

export const fetchCurriculums = async () => {
  const { data } = await axiosInstance.get(`${BASE}/curriculums/`);
  return data.curriculums || [];
};

export const fetchBatchStudents = async (batchId, params = {}) => {
  const { data } = await axiosInstance.get(`${BASE}/${batchId}/students/`, { params });
  return data;
};

export const createBatch = async (payload) => {
  const { data } = await axiosInstance.post(`${BASE}/create/`, payload);
  return data;
};

export const deleteBatch = async (batchId) => {
  const { data } = await axiosInstance.delete(`${BASE}/${batchId}/delete/`);
  return data;
};

export const saveStudentsBatch = async (payload) => {
  const { data } = await axiosInstance.post(`${BASE}/save-students/`, payload);
  return data;
};

export const addSingleStudent = async (payload) => {
  const { data } = await axiosInstance.post(`${BASE}/add-student/`, payload);
  return data;
};

export const getStudent = async (studentId) => {
  const { data } = await axiosInstance.get(`${BASE}/student/${studentId}/`);
  return data;
};

export const updateStudent = async (studentId, payload) => {
  const { data } = await axiosInstance.put(`${BASE}/student/${studentId}/update/`, payload);
  return data;
};

export const deleteStudent = async (studentId) => {
  const { data } = await axiosInstance.delete(`${BASE}/student/${studentId}/delete/`);
  return data;
};

export const updateStudentStatus = async (studentId, status) => {
  const { data } = await axiosInstance.post(`${BASE}/student/${studentId}/status/`, {
    reported_status: status,
  });
  return data;
};
