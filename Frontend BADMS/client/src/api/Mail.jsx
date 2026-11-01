import axiosInstance from "../context/axiosInstance";

export const mailBatch = async (batch) => {
  try {
    const response = await axiosInstance.post("/users/mail-batch/", {
      batch,
    });
    return response.data;
  } catch (error) {
    console.error(
      "Error mailing users:",
      error.response?.data || error.message,
    );
    throw error;
  }
};
