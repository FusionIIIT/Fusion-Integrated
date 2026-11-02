import axiosInstance from "../context/axiosInstance";
import { CONFIG } from "../pages/Login/constants";

/**
 * Authenticate against the backend.
 *
 * The server sets an httpOnly auth cookie, so there is no token to return, store, or
 * log here. Pure network concern; never logs the credentials.
 */
export const login = async (username, password) => {
  await axiosInstance.post(
    "/login/",
    { username, password },
    { timeout: CONFIG.API_TIMEOUT_MS },
  );
};
