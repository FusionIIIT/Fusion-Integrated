/** An unreachable identity service is not a logout.
 *
 *  Mapping every failure to "anonymous" sent people to the login page during an
 *  outage, where signing in could not work either.
 */
import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { RequireAuth } from "./RequireAuth";

const useAuth = vi.hoisted(() => vi.fn());
vi.mock("./AuthProvider", () => ({ useAuth }));

function renderAt(status: string, path = "/placement/reports") {
  useAuth.mockReturnValue({ status });
  return render(
    <MantineProvider>
      <MemoryRouter initialEntries={[path]}
                    future={{ v7_startTransition: true,
                              v7_relativeSplatPath: true }}>
        <Routes>
          <Route path="/login" element={<div>login screen</div>} />
          <Route path="/placement/reports"
                 element={<RequireAuth><div>the report</div></RequireAuth>} />
        </Routes>
      </MemoryRouter>
    </MantineProvider>,
  );
}

describe("RequireAuth", () => {
  it("renders the page when authenticated", () => {
    renderAt("authenticated");
    expect(screen.getByText("the report")).toBeInTheDocument();
  });

  it("sends an anonymous visitor to the login screen", () => {
    renderAt("anonymous");
    expect(screen.getByText("login screen")).toBeInTheDocument();
    expect(screen.queryByText("the report")).toBeNull();
  });

  it("shows a spinner while the session is still unknown", () => {
    renderAt("loading");
    expect(screen.queryByText("the report")).toBeNull();
    expect(screen.queryByText("login screen")).toBeNull();
  });

  it("says the session could not be verified, and does not redirect", () => {
    renderAt("unavailable");

    expect(screen.getByText(/cannot verify your session/i)).toBeInTheDocument();
    // The distinction that matters: they were not signed out, so they are not
    // sent somewhere that cannot help.
    expect(screen.getByText(/have not been signed out/i)).toBeInTheDocument();
    expect(screen.queryByText("login screen")).toBeNull();
    expect(screen.queryByText("the report")).toBeNull();
  });
});
