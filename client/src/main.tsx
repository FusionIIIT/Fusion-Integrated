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
      // 1, not the default 3: a 403 or 422 is a deterministic answer, and
      // retrying it three times just delays the error the user needs to see.
      retry: 1,
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
        <BrowserRouter>
          {/* AuthProvider is INSIDE the router — it redirects on 401. */}
          <AuthProvider>
            <AppRoutes />
          </AuthProvider>
        </BrowserRouter>
      </QueryClientProvider>
    </MantineProvider>
  </React.StrictMode>,
);
