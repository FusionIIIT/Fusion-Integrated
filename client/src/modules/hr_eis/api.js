import axios from 'axios';

const API_URL = '/api/v1/hr-eis/';

export const getEmployees = async () => {
    const response = await axios.get(`${API_URL}employees/`);
    return response.data;
};

export const getDepartments = async () => {
    const response = await axios.get(`${API_URL}departments/`);
    return response.data;
};

export const getPositions = async () => {
    const response = await axios.get(`${API_URL}positions/`);
    return response.data;
};
