/** Icons cross the wire as strings ("FaBriefcase"), so the server can name one
 *  without the client shipping every icon in the set.
 *
 *  Named imports ONLY. `import * as Fa` defeats tree-shaking and ships ~1 MB. */
import {
  FaBook, FaBriefcase, FaBuilding, FaBullhorn, FaCalendarAlt, FaChartBar,
  FaCheckDouble, FaCircle, FaClipboardCheck, FaClipboardList, FaCog,
  FaExternalLinkAlt,
  FaFileSignature, FaGraduationCap, FaIdBadge, FaIdCard, FaLayerGroup,
  FaSignOutAlt, FaThLarge, FaUserCheck, FaUserTie, FaUsers,
} from "react-icons/fa";
import type { IconType } from "react-icons";

export const ICONS = {
  FaBriefcase, FaBuilding, FaBullhorn, FaCalendarAlt, FaChartBar,
  FaCheckDouble, FaCircle, FaClipboardCheck, FaClipboardList, FaCog,
  FaExternalLinkAlt,
  FaFileSignature, FaGraduationCap, FaIdBadge, FaIdCard, FaLayerGroup,
  FaSignOutAlt, FaThLarge, FaUserCheck, FaUserTie, FaUsers,
} as const;

export type IconKey = keyof typeof ICONS;

// Module registries name Phosphor icons for Fusion-client; this client draws the nearest twin.
const PHOSPHOR: Record<string, IconType> = {
  Briefcase: FaBriefcase, Buildings: FaBuilding, CalendarBlank: FaCalendarAlt,
  ChartBar: FaChartBar, Checks: FaCheckDouble, ClipboardText: FaClipboardList,
  GraduationCap: FaGraduationCap, IdentificationCard: FaIdCard, Megaphone: FaBullhorn,
  Notebook: FaBook, Signature: FaFileSignature, UserCheck: FaUserCheck, Users: FaUsers,
};

export function resolveIcon(key: string | undefined): IconType {
  if (!key) return FaCircle;
  return (ICONS as Record<string, IconType>)[key] ?? PHOSPHOR[key] ?? FaCircle;
}
