import axiosInstance from "../context/axiosInstance";

export const createUser = async (userData) => {
  try {
    const response = await axiosInstance.post("/users/add/", userData);
    return response.data;
  } catch (error) {
    console.error(
      "Error creating user:",
      error.response?.data || error.message,
    );
    throw error;
  }
};

export const createFaculty = async (userData) => {
  try {
    const response = await axiosInstance.post("/users/add-faculty/", userData);
    return response.data;
  } catch (error) {
    console.error(
      "Error creating faculty:",
      error.response?.data || error.message,
    );
    throw error;
  }
};

export const createStaff = async (userData) => {
  try {
    const response = await axiosInstance.post("/users/add-staff/", userData);
    return response.data;
  } catch (error) {
    console.error(
      "Error creating staff:",
      error.response?.data || error.message,
    );
    throw error;
  }
};

export const resetPassword = async (userData) => {
  try {
    const response = await axiosInstance.post(
      "/users/reset_password/",
      userData,
    );
    return response.data;
  } catch (error) {
    console.error(
      "Error resetting password:",
      error.response?.data || error.message,
    );
    throw error;
  }
};

export const fetchUsersByType = async (type) => {
  try {
    const response = await axiosInstance.get("/users/", {
      params: { type },
    });
    return response.data;
  } catch (error) {
    console.error(
      "Error fetching users:",
      error.response?.data || error.message,
    );
    throw error;
  }
};
