import axios from "axios";

// The API lives under the app's own base path (Vite `base`), same-origin as the SPA,
// so the httpOnly auth cookie is always sent (dev: Vite proxy; prod: reverse proxy).
//   base "/"          -> "/api"
//   base "/sysadmin/" -> "/sysadmin/api"
const appBase = import.meta.env.BASE_URL.replace(/\/+$/, "");
const apiBaseUrl = `${appBase}/api`;

const axiosInstance = axios.create({
  baseURL: apiBaseUrl,
  // Auth is an httpOnly cookie set by the API — send it on every request. No token
  // is kept in JS, so an XSS flaw can't read it.
  withCredentials: true,
});

// If the cookie is missing/expired the API answers 401: drop the local "logged in"
// hint and bounce the user to the login screen.
axiosInstance.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("isAuthenticated");
      localStorage.removeItem("sessionStart");
      if (!window.location.pathname.startsWith("/login")) {
        window.location.assign("/login");
      }
    }
    return Promise.reject(error);
  },
);

export default axiosInstance;
