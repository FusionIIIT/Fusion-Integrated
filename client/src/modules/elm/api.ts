import { api } from '@fusion/core';

export const getLeaveTypes = () => api.get('/elm/leave-types/');

export const getLeaveBalances = () => api.get('/elm/leave-balances/');

export const getLeaveApplications = () => api.get('/elm/leave-applications/');

export const createLeaveApplication = (data: any) => api.post('/elm/leave-applications/', data);

export const getLeaveApplication = (id: number) => api.get(`/elm/leave-applications/${id}/`);
