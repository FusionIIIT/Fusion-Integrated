import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, useRoutes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { routes } from "./routes";

const auth = vi.hoisted(() => ({ can: vi.fn() }));
vi.mock("../../auth/AuthProvider", () => ({ useAuth: () => auth }));

function PmsRouter() {
  return useRoutes([{ path: "/pms", children: routes }]);
}

describe("PMS direct route guards", () => {
  beforeEach(() => auth.can.mockReturnValue(false));

  const paths = routes.flatMap((route) => route.path ? [route.path] : []);

  it.each(paths)("refuses direct access to /pms/%s without its permission", (path) => {
    render(
      <MantineProvider>
        <MemoryRouter initialEntries={[`/pms/${path}`]}>
          <main><PmsRouter /></main>
        </MemoryRouter>
      </MantineProvider>,
    );

    expect(screen.getByText("Not available to your role")).toBeInTheDocument();
    expect(screen.getByRole("main").querySelectorAll("button")).toHaveLength(0);
  });
});
