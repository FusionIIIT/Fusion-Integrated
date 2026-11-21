import { Button, Container, Group } from "@mantine/core";
import { NavLink, Outlet } from "react-router-dom";

const LINKS = [
  { to: "inbox", label: "Inbox" },
  { to: "outbox", label: "Outbox" },
  { to: "drafts", label: "Drafts" },
  { to: "new", label: "New file" },
];

/** In-module navigation, so the screens are reachable even before the server
 *  registers sidebar items for FTS. */
export function FtsLayout() {
  return (
    <Container size="lg">
      <Group gap="xs" mb="md">
        {LINKS.map((l) => (
          <NavLink key={l.to} to={l.to} end>
            {({ isActive }) => (
              <Button variant={isActive ? "light" : "subtle"} size="compact-md"
                      component="span">
                {l.label}
              </Button>
            )}
          </NavLink>
        ))}
      </Group>
      <Outlet />
    </Container>
  );
}

export default FtsLayout;
