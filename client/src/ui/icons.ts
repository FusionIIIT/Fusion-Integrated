/** Icons cross the wire as strings ("FaBriefcase"), so the server can name one
 *  without the client shipping every icon in the set.
 *
 *  Named imports ONLY. `import * as Fa` defeats tree-shaking and ships ~1 MB. */
import {
  FaBriefcase, FaBuilding, FaBullhorn, FaCalendarAlt, FaChartBar,
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

export function resolveIcon(key: string | undefined): IconType {
  return (key && (ICONS as Record<string, IconType>)[key]) || FaCircle;
}
