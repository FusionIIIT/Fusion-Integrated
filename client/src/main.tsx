import "@mantine/core/styles.css";
// Order matters: dates extends core's style layer, notifications sits on top.
import "@mantine/dates/styles.css";
import "@mantine/notifications/styles.css";

import { MantineProvider } from "@mantine/core";
import { Notifications } from "@mantine/notifications";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import { AppRoutes } from "./app/router";
import { AuthProvider } from "./auth/AuthProvider";
import { theme } from "./ui/theme/theme";

const qc = new QueryClient({
  defaultOptions: {
    queries: {
      // A 4xx is a deterministic answer: retrying it delays the error the user
      // needs to see and doubles it in the console.
      retry: (count, error) => {
        const status = (error as { response?: { status?: number } })
          ?.response?.status;
        if (status && status >= 400 && status < 500) return false;
        return count < 1;
      },
      staleTime: 30_000,
      refetchOnWindowFocus: true,
    },
  },
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <MantineProvider theme={theme} defaultColorScheme="light">
      <Notifications />
      <QueryClientProvider client={qc}>
        {/* Opted in now so the v7 upgrade is not also a behaviour change. */}
        <BrowserRouter
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        >
          {/* AuthProvider is INSIDE the router — it redirects on 401. */}
          <AuthProvider>
            <AppRoutes />
          </AuthProvider>
        </BrowserRouter>
      </QueryClientProvider>
    </MantineProvider>
  </React.StrictMode>,
);
