import type { NavGroup, NavGroupItem, NavLinkItem } from "../layout/AppShellLayout";

export interface FlatLink extends NavLinkItem {
  parent: string;
  section: string;
  nested: boolean;
}

export function flattenNavLinks(groups: NavGroup[]): FlatLink[] {
  return groups.flatMap((g) =>
    g.items.flatMap((item: NavGroupItem): FlatLink[] => {
      if (item.links) {
        return item.links.map((l) => ({
          ...l, parent: item.label, section: g.section, nested: true,
        }));
      }
      return item.to
        ? [{
            code: item.code, label: item.label, icon: item.icon, to: item.to,
            app: item.app, parent: g.section, section: g.section, nested: false,
          }]
        : [];
    }),
  );
}

export function findActiveLink(groups: NavGroup[], activePath: string): FlatLink | null {
  let best: FlatLink | null = null;
  flattenNavLinks(groups).forEach((link) => {
    if (activePath !== link.to && !activePath.startsWith(`${link.to}/`)) return;
    if (!best || link.to.length > best.to.length) best = link;
  });
  return best;
}

export function findActiveGroupCode(groups: NavGroup[], activePath: string): string | null {
  const match = findActiveLink(groups, activePath);
  if (!match) return null;
  const owner = groups
    .flatMap((g) => g.items)
    .find((item) => item.links?.some((l) => l.to === match.to));
  return owner?.code ?? null;
}
