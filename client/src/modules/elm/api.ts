import axios from 'axios';

const API_URL = 'http://localhost:8000/elm/';

export const fetchCourses = async () => {
    const response = await axios.get(`${API_URL}courses/`);
    return response.data;
};
