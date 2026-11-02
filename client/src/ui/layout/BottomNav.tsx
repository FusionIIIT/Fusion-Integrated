import { Text, UnstyledButton } from "@mantine/core";
import { FaEllipsisH } from "react-icons/fa";
import type { IconType } from "react-icons";

import { resolveIcon } from "../icons";
import classes from "./BottomNav.module.css";

export interface BottomNavItem {
  code: string;
  label: string;
  icon?: string;
  to: string;
}

interface ItemProps {
  label: string;
  icon: IconType;
  active?: boolean;
  onClick: () => void;
}

function Item({ label, icon: Icon, active, onClick }: ItemProps) {
  return (
    <UnstyledButton
      className={classes.item}
      data-active={active || undefined}
      onClick={onClick}
      aria-current={active ? "page" : undefined}
    >
      <span className={classes.rule} />
      <Icon size={20} />
      <Text className={classes.label}>{label}</Text>
    </UnstyledButton>
  );
}

interface Props {
  items: BottomNavItem[];
  activeTo: string | null;
  onNavigate: (to: string) => void;
  onMore: () => void;
  moreActive?: boolean;
}

export function BottomNav({ items, activeTo, onNavigate, onMore, moreActive }: Props) {
  return (
    <nav className={classes.bar} aria-label="Primary">
      {items.map((item) => (
        <Item
          key={item.code}
          label={item.label}
          icon={resolveIcon(item.icon)}
          active={activeTo === item.to}
          onClick={() => onNavigate(item.to)}
        />
      ))}
      <Item label="More" icon={FaEllipsisH} active={moreActive} onClick={onMore} />
    </nav>
  );
}

export default BottomNav;
