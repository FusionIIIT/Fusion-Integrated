/** Icons cross the wire as strings ("FaBriefcase"), so the server can name one
 *  without the client shipping every icon in the set.
 *
 *  Named imports ONLY. `import * as Fa` defeats tree-shaking and ships ~1 MB. */
import {
  FaBriefcase, FaBuilding, FaBullhorn, FaCalendarAlt, FaChartBar, FaChartPie,
  FaCheckDouble, FaCircle, FaClipboardCheck, FaClipboardList, FaCog,
  FaEdit, FaExternalLinkAlt,
  FaFileSignature, FaGraduationCap, FaIdBadge, FaIdCard, FaLayerGroup,
  FaListAlt, FaQuestionCircle,
  FaSignOutAlt, FaThLarge, FaUserCheck, FaUserTie, FaUsers,
} from "react-icons/fa";
import type { IconType } from "react-icons";

export const ICONS = {
  FaBriefcase, FaBuilding, FaBullhorn, FaCalendarAlt, FaChartBar, FaChartPie,
  FaCheckDouble, FaCircle, FaClipboardCheck, FaClipboardList, FaCog,
  FaEdit, FaExternalLinkAlt,
  FaFileSignature, FaGraduationCap, FaIdBadge, FaIdCard, FaLayerGroup,
  FaListAlt, FaQuestionCircle,
  FaSignOutAlt, FaThLarge, FaUserCheck, FaUserTie, FaUsers,
} as const;

export type IconKey = keyof typeof ICONS;

export function resolveIcon(key: string | undefined): IconType {
  if (!key) return FaCircle;
  const icons = ICONS as Record<string, IconType>;
  return icons[key] || icons[`Fa${key}`] || FaCircle;
}
