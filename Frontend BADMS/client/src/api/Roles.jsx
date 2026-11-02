import axiosInstance from "../context/axiosInstance";

export const createCustomRole = async (roleData) => {
  try {
    const response = await axiosInstance.post("/create-role/", roleData);
    return response.data;
  } catch (error) {
    console.error(
      "Error creating custom role:",
      error.response?.data || error.message,
    );
    throw error;
  }
};

export const getAllRoles = async () => {
  try {
    const response = await axiosInstance.get("/view-roles/");
    return response.data;
  } catch (error) {
    console.error(
      "Error fetching roles:",
      error.response?.data || error.message,
    );
    throw error;
  }
};

export const getAllDesignations = async (designationType) => {
  try {
    const response = await axiosInstance.post(
      "/view-designations/",
      designationType,
    );
    return response.data;
  } catch (error) {
    console.error(
      "Error fetching designations:",
      error.response?.data || error.message,
    );
    throw error;
  }
};

export const getAllDepartments = async () => {
  try {
    const response = await axiosInstance.get("/departments/");
    return response.data;
  } catch (error) {
    console.error(
      "Error fetching departments:",
      error.response?.data || error.message,
    );
    throw error;
  }
};

export const getAllBatches = async () => {
  try {
    const response = await axiosInstance.get("/batches/");
    return response.data;
  } catch (error) {
    console.error(
      "Error fetching batches:",
      error.response?.data || error.message,
    );
    throw error;
  }
};
