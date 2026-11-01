/* eslint-disable react/prop-types */
import { useMemo, useState } from "react";
import {
  ActionIcon,
  AppShell,
  Avatar,
  Box,
  Burger,
  Button,
  Group,
  NavLink,
  ScrollArea,
  Text,
  TextInput,
  Tooltip,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { useLocation, useNavigate } from "react-router-dom";
import { FaSearch, FaSignOutAlt, FaUserShield } from "react-icons/fa";
import { useAuth } from "../../context/AuthContext";
import { ALL_LINKS, NAV_GROUPS } from "./navConfig";
import logo from "../../assets/iiitdmj_logo.png";
import classes from "./AppLayout.module.css";

const today = () =>
  new Date()
    .toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })
    .toUpperCase();

const AppLayout = ({ children }) => {
  const [opened, { toggle, close }] = useDisclosure();
  const [query, setQuery] = useState("");
  const { pathname } = useLocation();
  const [openGroup, setOpenGroup] = useState(() => {
    for (const g of NAV_GROUPS)
      for (const it of g.items)
        if (it.links && it.links.some((l) => l.to === pathname)) return it.label;
    return null;
  });
  const navigate = useNavigate();
  const { logout } = useAuth();

  const go = (to) => {
    navigate(to);
    setQuery("");
    close();
  };

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const linkClasses = { root: classes.navLink };
  const term = query.trim().toLowerCase();
  const results = useMemo(
    () =>
      term
        ? ALL_LINKS.filter(
            (l) => l.label.toLowerCase().includes(term) || l.parent.toLowerCase().includes(term),
          )
        : null,
    [term],
  );

  const renderItem = (item) =>
    item.links ? (
      <NavLink
        key={item.label}
        classNames={linkClasses}
        label={item.label}
        leftSection={<item.icon size={16} />}
        opened={openGroup === item.label}
        onClick={() => setOpenGroup((cur) => (cur === item.label ? null : item.label))}
        childrenOffset={20}
      >
        {item.links.map((link) => (
          <NavLink
            key={link.to}
            classNames={linkClasses}
            label={link.label}
            leftSection={<link.icon size={13} />}
            active={pathname === link.to}
            onClick={() => go(link.to)}
          />
        ))}
      </NavLink>
    ) : (
      <NavLink
        key={item.to}
        classNames={linkClasses}
        label={item.label}
        leftSection={<item.icon size={16} />}
        active={pathname === item.to}
        onClick={() => go(item.to)}
      />
    );

  return (
    <AppShell
      header={{ height: 66 }}
      navbar={{ width: 280, breakpoint: "sm", collapsed: { mobile: !opened } }}
      padding="lg"
    >
      <AppShell.Header className={classes.header}>
        <Group h="100%" px="lg" justify="space-between" wrap="nowrap">
          <Group gap="md" wrap="nowrap">
            <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" />
            <img src={logo} alt="PDPM IIITDM Jabalpur" style={{ height: 40 }} />
            <Box className={classes.brand} visibleFrom="xs">
              <Text fw={900} size="sm" lts={1} c="#0b1220">
                PDPM IIITDM <span style={{ color: "#15abff" }}>JABALPUR</span>
              </Text>
              <Text size="xs" c="dimmed" fw={800} style={{ fontFamily: "monospace", letterSpacing: 2 }}>
                FUSION · SYSTEM ADMINISTRATOR
              </Text>
            </Box>
          </Group>
          <Group gap="lg" wrap="nowrap">
            <Text size="xs" c="dimmed" fw={800} visibleFrom="sm" style={{ fontFamily: "monospace" }}>
              {today()}
            </Text>
            <Button
              variant="light"
              color="red"
              size="xs"
              leftSection={<FaSignOutAlt size={13} />}
              onClick={handleLogout}
            >
              Logout
            </Button>
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar className={classes.navbar}>
        <Box className={classes.search}>
          <TextInput
            classNames={{ input: classes.searchInput }}
            placeholder="Search…"
            size="sm"
            radius="md"
            leftSection={<FaSearch size={12} />}
            value={query}
            onChange={(e) => setQuery(e.currentTarget.value)}
          />
        </Box>

        <ScrollArea className={classes.scroll} type="auto" scrollbarSize={6}>
          {results ? (
            results.length ? (
              results.map((link) => (
                <NavLink
                  key={link.to}
                  classNames={linkClasses}
                  label={link.label}
                  description={link.parent}
                  leftSection={<link.icon size={14} />}
                  active={pathname === link.to}
                  onClick={() => go(link.to)}
                />
              ))
            ) : (
              <Text c="dimmed" size="sm" ta="center" mt="lg">
                No matches
              </Text>
            )
          ) : (
            NAV_GROUPS.map((group) => (
              <Box key={group.section}>
                <Text className={classes.sectionLabel}>{group.section}</Text>
                {group.items.map(renderItem)}
              </Box>
            ))
          )}
        </ScrollArea>

        <Box className={classes.footer}>
          <Avatar color="blue" radius="md" size={38} variant="filled">
            <FaUserShield size={16} />
          </Avatar>
          <div style={{ flex: 1, minWidth: 0 }}>
            <Text className={classes.footerName} truncate>
              Administrator
            </Text>
            <Text className={classes.footerRole}>System Operator</Text>
          </div>
          <Tooltip label="Log out" position="top" withArrow>
            <ActionIcon variant="subtle" className={classes.footerLogout} onClick={handleLogout} aria-label="Log out">
              <FaSignOutAlt size={15} />
            </ActionIcon>
          </Tooltip>
        </Box>
      </AppShell.Navbar>

      <AppShell.Main bg="gray.0">{children}</AppShell.Main>
    </AppShell>
  );
};

export default AppLayout;
