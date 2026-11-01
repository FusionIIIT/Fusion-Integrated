/** Ported from Fusion-client's shell, so the two apps look like one product. */
import {
  ActionIcon, AppShell, Avatar, Badge, Box, Burger, Button, Group, Indicator,
  NavLink, ScrollArea, Text, TextInput, Tooltip, UnstyledButton,
} from "@mantine/core";
import { useDisclosure, useMediaQuery } from "@mantine/hooks";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  FaAngleLeft, FaAngleRight, FaBell, FaSearch, FaSignOutAlt,
} from "react-icons/fa";

import logoDesktop from "../../assets/iiitdmj_logo.png";
import logoMobile from "../../assets/IIITJ_logo.webp";
import { resolveIcon } from "../icons";
import { findActiveGroupCode, findActiveLink, flattenNavLinks } from "../nav/match";
import { BottomNav, type BottomNavItem } from "./BottomNav";
import classes from "./AppShellLayout.module.css";

const BOTTOM_NAV_HEIGHT = 58;
const NAVBAR_WIDTH = 280;
const RAIL_WIDTH = 68;
const NAV_MAX_VIEWPORT_SHARE = 0.15;
const PEEK_DELAY_MS = 120;
const MAIN_ID = "page-content";
const COMPACT_BELOW = Math.round(NAVBAR_WIDTH / NAV_MAX_VIEWPORT_SHARE);
const OPEN_GROUPS_KEY = "fusion.nav.openGroups";
const RAIL_KEY = "fusion.nav.rail";

export interface NavLinkItem {
  code: string;
  label: string;
  icon?: string;
  to: string;
  /** Which Fusion app serves this path. Absent means this one. */
  app?: string;
}
export interface NavGroupItem {
  code: string;
  label: string;
  icon?: string;
  to?: string;
  app?: string;
  links?: NavLinkItem[];
}
export interface NavGroup {
  section: string;
  items: NavGroupItem[];
}

/** Where each sibling app lives. Ports in dev, path prefixes behind one origin
 *  in prod, so the IAM stores the app name and never a URL. */
const APP_BASES: Record<string, string> = JSON.parse(
  import.meta.env.VITE_APP_BASES || "{}",
);
const SELF = import.meta.env.VITE_APP_NAME || "integrated";

function externalHref(app: string | undefined, to: string): string | null {
  // Another app needs a full page load even same-origin: its bundle is not ours.
  if (!app || app === SELF) return null;
  const base = APP_BASES[app];
  return base ? `${base.replace(/\/$/, "")}${to}` : to;
}

function readStored<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw === null ? fallback : (JSON.parse(raw) as T);
  } catch {
    return fallback;
  }
}

function writeStored(key: string, value: unknown): void {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* private window or storage disabled; the sidebar still works */
  }
}

const today = () =>
  new Date()
    .toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })
    .toUpperCase();

/** Honorifics carried in display_name would otherwise become the first initial. */
const HONORIFIC = /^(mr|mrs|ms|dr|prof|shri|smt)\.?$/i;

function initials(name: string): string {
  const words = String(name || "").trim().split(/\s+/).filter(Boolean);
  const named = words.filter((w) => !HONORIFIC.test(w));
  return (named.length ? named : words)
    .slice(0, 2)
    .map((w) => w[0] ?? "")
    .join("")
    .toUpperCase() || "?";
}

interface Props {
  navGroups: NavGroup[];
  activePath: string;
  onNavigate: (to: string) => void;
  brandSubtitle: string;
  user: { name: string; roleLabel?: string; photo?: string };
  onLogout: () => void;
  profilePath?: string;
  roles?: string[];
  role?: string | null;
  onRoleChange?: (role: string) => void;
  unreadCount?: number;
  onBellClick?: () => void;
  bottomNavItems?: BottomNavItem[];
  navCounts?: Record<string, number>;
  children: React.ReactNode;
}

export function AppShellLayout({
  navGroups,
  activePath,
  onNavigate,
  brandSubtitle,
  user,
  onLogout,
  profilePath = "",
  roles = [],
  role = null,
  onRoleChange = () => {},
  unreadCount = 0,
  onBellClick = () => {},
  bottomNavItems = [],
  navCounts = {},
  children,
}: Props) {
  const [opened, { toggle }] = useDisclosure();
  const [query, setQuery] = useState("");
  const activeGroup = findActiveGroupCode(navGroups, activePath);
  const [openGroups, setOpenGroups] = useState<string[]>(() => {
    const stored = readStored<string[]>(OPEN_GROUPS_KEY, []);
    return Array.isArray(stored) ? stored : [];
  });
  const [railOverride, setRailOverride] = useState<boolean | null>(() => {
    const stored = readStored<boolean | null>(RAIL_KEY, null);
    return typeof stored === "boolean" ? stored : null;
  });
  const isNarrow = useMediaQuery("(max-width: 767px)");
  const isCompact = useMediaQuery(`(max-width: ${COMPACT_BELOW}px)`, false, {
    getInitialValueInEffect: false,
  });
  const showBottomNav = Boolean(isNarrow && bottomNavItems.length);
  const rail = Boolean((railOverride ?? isCompact) && !isNarrow);
  const [hovered, setHovered] = useState(false);
  const [focusWithin, setFocusWithin] = useState(false);
  const [peekArmed, setPeekArmed] = useState(true);
  const peeking = (hovered && peekArmed) || focusWithin;
  const compactNav = rail && !peeking;
  const viewportRef = useRef<HTMLDivElement>(null);
  const wasCompact = useRef(isCompact);
  const peekTimer = useRef<ReturnType<typeof setTimeout>>();
  const firstRender = useRef(true);

  useEffect(() => {
    if (activeGroup)
      setOpenGroups((cur) => (cur.includes(activeGroup) ? cur : [...cur, activeGroup]));
  }, [activeGroup]);

  useEffect(() => { writeStored(OPEN_GROUPS_KEY, openGroups); }, [openGroups]);

  useEffect(() => {
    if (wasCompact.current === isCompact) return;
    wasCompact.current = isCompact;
    setRailOverride(null);
  }, [isCompact]);

  useEffect(() => { writeStored(RAIL_KEY, railOverride); }, [railOverride]);

  useEffect(() => () => clearTimeout(peekTimer.current), []);

  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    const main = document.getElementById(MAIN_ID);
    const target = (main?.querySelector("h1") ?? main) as HTMLElement | null;
    if (!target) return;
    target.tabIndex = -1;
    target.focus({ preventScroll: true });
  }, [activePath]);

  const allLinks = useMemo(() => flattenNavLinks(navGroups), [navGroups]);
  const activeTo = useMemo(
    () => findActiveLink(navGroups, activePath)?.to ?? null,
    [navGroups, activePath],
  );

  useEffect(() => {
    if (query) return undefined;
    const timer = setTimeout(() => {
      const viewport = viewportRef.current;
      const active = viewport?.querySelector("[data-active]");
      if (!active || !viewport) return;
      const link = active.getBoundingClientRect();
      const frame = viewport.getBoundingClientRect();
      if (link.top < frame.top) viewport.scrollBy({ top: link.top - frame.top - 12 });
      else if (link.bottom > frame.bottom)
        viewport.scrollBy({ top: link.bottom - frame.bottom + 12 });
    }, 260);
    return () => clearTimeout(timer);
  }, [activeTo, compactNav, query]);

  const results = query.trim()
    ? allLinks.filter((l) => l.label.toLowerCase().includes(query.trim().toLowerCase()))
    : null;

  const go = (to: string, app?: string) => {
    const href = externalHref(app, to);
    if (href) { window.location.assign(href); return; }
    onNavigate(to);
    setQuery("");
    if (opened) toggle();
  };

  const navLinkClasses = {
    root: classes.navLink,
    section: classes.navLinkSection,
    body: classes.navLinkBody,
  };

  const followLink = (event: React.MouseEvent, to?: string, app?: string) => {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    if (to) go(to, app);
  };

  const toggleGroup = (code: string) => {
    if (compactNav) {
      setRailOverride(false);
      setOpenGroups((cur) => (cur.includes(code) ? cur : [...cur, code]));
      return;
    }
    setOpenGroups((cur) =>
      cur.includes(code) ? cur.filter((c) => c !== code) : [...cur, code]);
  };

  const withTooltip = (key: string, label: string, node: React.ReactElement) => (
    <Tooltip key={key} label={label} position="right" withArrow offset={10}
             disabled={!compactNav}>
      {node}
    </Tooltip>
  );

  const labelWith = (text: string, count: number) =>
    count ? (
      <Group justify="space-between" gap="xs" wrap="nowrap">
        <span className={classes.navLabelText}>{text}</span>
        <Badge size="xs" variant="filled" color="blue" circle={count < 10}>
          {count > 99 ? "99+" : count}
        </Badge>
      </Group>
    ) : (
      text
    );

  const renderItem = (item: NavGroupItem) => {
    const Icon = resolveIcon(item.icon);
    if (item.links) {
      const isOpen = !compactNav && openGroups.includes(item.code);
      const holdsActive = item.links.some((link) => link.to === activeTo);
      const groupCount = item.links.reduce((s, l) => s + (navCounts[l.to] ?? 0), 0);
      return withTooltip(
        item.code,
        item.label,
        <NavLink
          key={item.code}
          component="button"
          type="button"
          classNames={navLinkClasses}
          label={isOpen ? item.label : labelWith(item.label, groupCount)}
          leftSection={<Icon size={16} />}
          opened={isOpen}
          aria-expanded={isOpen}
          data-holds-active={!isOpen && holdsActive ? "true" : undefined}
          data-pending={groupCount ? "true" : undefined}
          onClick={() => toggleGroup(item.code)}
          childrenOffset={20}
        >
          {item.links.map((link) => {
            const LinkIcon = resolveIcon(link.icon);
            const isActive = activeTo === link.to;
            return (
              <NavLink
                key={link.code}
                classNames={navLinkClasses}
                label={labelWith(link.label, navCounts[link.to] ?? 0)}
                leftSection={<LinkIcon size={13} />}
                active={isActive}
                data-pending={navCounts[link.to] ? "true" : undefined}
                aria-current={isActive ? "page" : undefined}
                component="a"
                href={externalHref(link.app, link.to) ?? link.to}
                onClick={(e: React.MouseEvent) => followLink(e, link.to, link.app)}
              />
            );
          })}
        </NavLink>,
      );
    }
    const isActive = activeTo === item.to;
    const to = item.to ?? "";
    return withTooltip(
      item.code,
      item.label,
      <NavLink
        key={item.code}
        classNames={navLinkClasses}
        label={labelWith(item.label, navCounts[to] ?? 0)}
        leftSection={<Icon size={16} />}
        active={isActive}
        data-pending={navCounts[to] ? "true" : undefined}
        aria-current={isActive ? "page" : undefined}
        component="a"
        href={externalHref(item.app, to) ?? to}
        onClick={(e: React.MouseEvent) => followLink(e, item.to, item.app)}
      />,
    );
  };

  return (
    <AppShell
      header={{ height: 66 }}
      navbar={{
        width: rail ? RAIL_WIDTH : NAVBAR_WIDTH,
        breakpoint: "sm",
        collapsed: { mobile: !opened },
      }}
      footer={{ height: BOTTOM_NAV_HEIGHT, collapsed: !showBottomNav }}
      padding={{ base: "sm", sm: "lg" }}
    >
      <a href={`#${MAIN_ID}`} className={classes.skipLink}>Skip to content</a>

      <AppShell.Header className={classes.header}>
        <Group h="100%" justify="space-between" wrap="nowrap"
               className={classes.headerInner}>
          <Group gap="sm" wrap="nowrap" className={classes.headerLeft}>
            <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" />
            <Box component="img" src={logoMobile} alt="PDPM IIITDM Jabalpur"
                 h={32} hiddenFrom="sm" />
            <Box component="img" src={logoDesktop} alt="PDPM IIITDM Jabalpur"
                 h={40} visibleFrom="sm" />
            <Box className={classes.brand} visibleFrom="md">
              <Text fw={900} size="sm" lts={1} c="#0b1220">
                PDPM IIITDM <span style={{ color: "#15abff" }}>JABALPUR</span>
              </Text>
              <Text size="xs" c="dimmed" fw={800}
                    style={{ fontFamily: "monospace", letterSpacing: 2 }}>
                {brandSubtitle}
              </Text>
            </Box>
          </Group>
          <Group gap="sm" wrap="nowrap" className={classes.headerRight}>
            <Text size="xs" c="dimmed" fw={800} visibleFrom="lg"
                  style={{ fontFamily: "monospace" }}>
              {today()}
            </Text>
            <Indicator label={unreadCount > 99 ? "99+" : unreadCount} size={16}
                       color="red" disabled={!unreadCount}>
              <ActionIcon variant="subtle" className={classes.bell}
                          onClick={onBellClick} aria-label="Notifications">
                <FaBell size={18} />
              </ActionIcon>
            </Indicator>
            <Button variant="light" color="red" size="xs"
                    leftSection={<FaSignOutAlt size={14} />}
                    onClick={onLogout} visibleFrom="sm">
              Logout
            </Button>
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar
        className={classes.navbar}
        p={0}
        aria-label="Main navigation"
        data-rail={compactNav || undefined}
        data-peek={rail && peeking ? "true" : undefined}
        style={{ "--nav-expanded-width": `${NAVBAR_WIDTH}px` } as React.CSSProperties}
        onMouseEnter={() => {
          clearTimeout(peekTimer.current);
          peekTimer.current = setTimeout(() => setHovered(true), PEEK_DELAY_MS);
        }}
        onMouseLeave={() => {
          clearTimeout(peekTimer.current);
          setHovered(false);
          setPeekArmed(true);
          setFocusWithin(false);
        }}
      >
        <Box className={classes.navTop}>
          {!compactNav && (
            <TextInput
              className={classes.search}
              placeholder="Search"
              size="xs"
              leftSection={<FaSearch size={13} />}
              value={query}
              onChange={(e) => setQuery(e.currentTarget.value)}
            />
          )}
          <Tooltip label={rail ? "Expand sidebar" : "Collapse sidebar"}
                   position="right" withArrow>
            <ActionIcon
              variant="subtle"
              className={classes.railToggle}
              onClick={() => {
                setQuery("");
                setPeekArmed(rail);
                setRailOverride(!rail);
              }}
              aria-label={rail ? "Expand sidebar" : "Collapse sidebar"}
              aria-pressed={rail}
              visibleFrom="sm"
            >
              {rail ? <FaAngleRight size={14} /> : <FaAngleLeft size={14} />}
            </ActionIcon>
          </Tooltip>
        </Box>

        <ScrollArea
          className={classes.scroll}
          type="auto"
          scrollbarSize={6}
          viewportRef={viewportRef}
          onFocusCapture={() => setFocusWithin(true)}
          onBlurCapture={(event) => {
            if (!event.currentTarget.contains(event.relatedTarget as Node))
              setFocusWithin(false);
          }}
        >
          {results ? (
            results.length ? (
              results.map((link) => {
                const Icon = resolveIcon(link.icon);
                const isActive = activeTo === link.to;
                return (
                  <NavLink
                    key={`${link.parent}-${link.code}`}
                    classNames={navLinkClasses}
                    label={link.label}
                    description={link.parent}
                    leftSection={<Icon size={13} />}
                    active={isActive}
                    aria-current={isActive ? "page" : undefined}
                    component="a"
                    href={externalHref(link.app, link.to) ?? link.to}
                    onClick={(e: React.MouseEvent) => followLink(e, link.to, link.app)}
                  />
                );
              })
            ) : (
              <Text c="dimmed" size="sm" ta="center" mt="lg">No matches</Text>
            )
          ) : (
            navGroups.map((group) => (
              <Box key={group.section}>
                {compactNav ? (
                  <Box className={classes.railDivider} />
                ) : (
                  <Text className={classes.sectionLabel}>{group.section}</Text>
                )}
                {group.items.map(renderItem)}
              </Box>
            ))
          )}
        </ScrollArea>

        <Box className={classes.footer}>
          <Tooltip label={user.name} position="right" withArrow disabled={!compactNav}>
            <UnstyledButton
              className={classes.footerAvatar}
              onClick={() => profilePath && go(profilePath)}
              aria-label="Open my profile"
            >
              <Avatar
                color="blue"
                radius="md"
                size={compactNav ? 32 : 38}
                variant="filled"
                src={user.photo || null}
                imageProps={{ style: { objectFit: "cover" } }}
                alt={user.name}
              >
                {initials(user.name)}
              </Avatar>
            </UnstyledButton>
          </Tooltip>
          <div className={classes.footerDetails}>
            <UnstyledButton
              className={classes.footerNameButton}
              onClick={() => profilePath && go(profilePath)}
            >
              <Text className={classes.footerName} truncate>{user.name}</Text>
            </UnstyledButton>
            {roles.length > 1 ? (
              <select
                className={classes.footerRoleSelect}
                aria-label="Switch role"
                value={role ?? ""}
                onChange={(event) => onRoleChange(event.currentTarget.value)}
              >
                {roles.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
            ) : (
              <Text className={classes.footerRole} truncate>{user.roleLabel}</Text>
            )}
          </div>
          <Tooltip label="Log out" position="top" withArrow>
            <ActionIcon variant="subtle" className={classes.footerLogout}
                        onClick={onLogout} aria-label="Log out">
              <FaSignOutAlt size={16} />
            </ActionIcon>
          </Tooltip>
        </Box>
      </AppShell.Navbar>

      <AppShell.Main bg="gray.0" id={MAIN_ID} tabIndex={-1} className={classes.main}>
        {children}
      </AppShell.Main>

      {showBottomNav && (
        <AppShell.Footer withBorder={false}>
          <BottomNav
            items={bottomNavItems}
            activeTo={activeTo}
            onNavigate={go}
            onMore={toggle}
            moreActive={opened}
          />
        </AppShell.Footer>
      )}
    </AppShell>
  );
}

export default AppShellLayout;
