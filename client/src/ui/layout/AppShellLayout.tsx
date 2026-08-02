/**
 * The shell. Ported from Fusion_System_Administrator's AppLayout.jsx with the
 * same markup, class names and sizes. Deliberate differences: `navGroups` is a
 * prop so the server decides what appears; it is typed; the avatar shows real
 * initials; and the logo swaps to the compact mark below `sm`.
 *
 * Identity lives in the sidebar footer and NOWHERE else — a long
 * "MR. FIRSTNAME LASTNAME · Designation" crowds the header out at laptop
 * widths once the logo lockup is in.
 */
import {
  ActionIcon, AppShell, Avatar, Box, Burger, Button, Group, NavLink, ScrollArea,
  Text, TextInput, Tooltip,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { useMemo, useState } from "react";
import { FaSearch, FaSignOutAlt } from "react-icons/fa";

import logoDesktop from "../../assets/iiitdmj_logo.png";
import logoMobile from "../../assets/IIITJ_logo.webp";
import { resolveIcon } from "../icons";
import classes from "./AppShellLayout.module.css";

const today = () =>
  new Date()
    .toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })
    .toUpperCase();

/** Honorifics carried in display_name would otherwise become the first initial. */
const HONORIFIC = /^(mr|mrs|ms|dr|prof|shri|smt)\.?$/i;

function initials(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean);
  const named = words.filter((w) => !HONORIFIC.test(w));
  return (named.length ? named : words)
    .slice(0, 2)
    .map((w) => w[0] ?? "")
    .join("")
    .toUpperCase() || "?";
}

export interface NavLinkItem {
  code: string;
  label: string;
  icon?: string;
  to: string;
}
export interface NavGroupItem {
  code: string;
  label: string;
  icon?: string;
  to?: string;
  links?: NavLinkItem[];
}
export interface NavGroup {
  section: string;
  items: NavGroupItem[];
}

interface Props {
  navGroups: NavGroup[];
  activePath: string;
  onNavigate: (to: string) => void;
  brandSubtitle: string;
  user: { name: string; roleLabel: string };
  onLogout: () => void;
  children: React.ReactNode;
}

/** Flattened link list, for the search box. */
function flatten(groups: NavGroup[]): (NavLinkItem & { parent: string })[] {
  return groups.flatMap((g) =>
    g.items.flatMap((item) =>
      item.links
        ? item.links.map((l) => ({ ...l, parent: item.label }))
        : item.to
          ? [{ code: item.code, label: item.label, icon: item.icon, to: item.to,
               parent: g.section }]
          : [],
    ),
  );
}

export function AppShellLayout({
  navGroups, activePath, onNavigate, brandSubtitle, user, onLogout, children,
}: Props) {
  const [opened, { toggle }] = useDisclosure();
  const [query, setQuery] = useState("");
  const [openGroup, setOpenGroup] = useState<string | null>(
    () => navGroups.find((g) => g.items.some((i) =>
      i.links?.some((l) => activePath.startsWith(l.to))))?.items[0]?.label ?? null,
  );

  const allLinks = useMemo(() => flatten(navGroups), [navGroups]);
  const results = query.trim()
    ? allLinks.filter((l) =>
        l.label.toLowerCase().includes(query.trim().toLowerCase()))
    : null;

  const go = (to: string) => { onNavigate(to); if (opened) toggle(); };

  const renderItem = (item: NavGroupItem) => {
    const Icon = resolveIcon(item.icon);
    if (item.links) {
      return (
        <NavLink
          key={item.code}
          classNames={{ root: classes.navLink }}
          label={item.label}
          leftSection={<Icon size={16} />}
          opened={openGroup === item.label}
          onClick={() =>
            setOpenGroup((cur) => (cur === item.label ? null : item.label))}
          childrenOffset={20}
        >
          {item.links.map((link) => {
            const LinkIcon = resolveIcon(link.icon);
            return (
              <NavLink
                key={link.code}
                classNames={{ root: classes.navLink }}
                label={link.label}
                leftSection={<LinkIcon size={13} />}
                active={activePath === link.to}
                onClick={() => go(link.to)}
              />
            );
          })}
        </NavLink>
      );
    }
    return (
      <NavLink
        key={item.code}
        classNames={{ root: classes.navLink }}
        label={item.label}
        leftSection={<Icon size={16} />}
        active={activePath === item.to}
        onClick={() => item.to && go(item.to)}
      />
    );
  };

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
            <Box
              component="img" src={logoMobile} alt="PDPM IIITDM Jabalpur"
              h={36} hiddenFrom="sm"
            />
            <Box
              component="img" src={logoDesktop} alt="PDPM IIITDM Jabalpur"
              h={40} visibleFrom="sm"
            />
            <Box className={classes.brand} visibleFrom="xs">
              <Text fw={900} size="sm" lts={1} c="#0b1220">
                PDPM IIITDM <span style={{ color: "#15abff" }}>JABALPUR</span>
              </Text>
              <Text
                size="xs" c="dimmed" fw={800}
                style={{ fontFamily: "monospace", letterSpacing: 2 }}
              >
                {brandSubtitle}
              </Text>
            </Box>
          </Group>
          <Group gap="lg" wrap="nowrap">
            <Text
              size="xs" c="dimmed" fw={800} visibleFrom="sm"
              style={{ fontFamily: "monospace" }}
            >
              {today()}
            </Text>
            <Button
              variant="light" color="red" size="xs"
              leftSection={<FaSignOutAlt size={13} />}
              onClick={onLogout}
            >
              Logout
            </Button>
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar className={classes.navbar} p={0}>
        <Box p="md" pb={4}>
          <TextInput
            className={classes.search}
            placeholder="Search"
            size="xs"
            leftSection={<FaSearch size={12} />}
            value={query}
            onChange={(e) => setQuery(e.currentTarget.value)}
          />
        </Box>

        <ScrollArea className={classes.scroll} type="auto" scrollbarSize={6}>
          {results
            ? results.length
              ? results.map((link) => {
                  const Icon = resolveIcon(link.icon);
                  return (
                    <NavLink
                      key={link.code}
                      classNames={{ root: classes.navLink }}
                      label={link.label}
                      description={link.parent}
                      leftSection={<Icon size={13} />}
                      active={activePath === link.to}
                      onClick={() => go(link.to)}
                    />
                  );
                })
              : (
                <Text c="dimmed" size="sm" ta="center" mt="lg">
                  No matches
                </Text>
              )
            : navGroups.map((group) => (
                <Box key={group.section}>
                  <Text className={classes.sectionLabel}>{group.section}</Text>
                  {group.items.map(renderItem)}
                </Box>
              ))}
        </ScrollArea>

        <Box className={classes.footer}>
          <Avatar color="blue" radius="md" size={38} variant="filled">
            {initials(user.name)}
          </Avatar>
          <div style={{ flex: 1, minWidth: 0 }}>
            <Text className={classes.footerName} truncate>{user.name}</Text>
            <Text className={classes.footerRole} truncate>{user.roleLabel}</Text>
          </div>
          <Tooltip label="Log out" position="top" withArrow>
            <ActionIcon
              variant="subtle" className={classes.footerLogout}
              onClick={onLogout} aria-label="Log out"
            >
              <FaSignOutAlt size={15} />
            </ActionIcon>
          </Tooltip>
        </Box>
      </AppShell.Navbar>

      <AppShell.Main bg="gray.0">{children}</AppShell.Main>
    </AppShell>
  );
}
