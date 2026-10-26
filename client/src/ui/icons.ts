/** Icons cross the wire as strings ("FaBriefcase" or "CalendarBlank"), so the server can name one
 *  without the client shipping every icon in the set.
 *
 *  Named imports ONLY. `import * as Fa` defeats tree-shaking and ships ~1 MB. */
import {
  FaBalanceScale, FaBriefcase, FaBuilding, FaBullhorn, FaCalendarAlt,
  FaCalendarCheck, FaChartBar, FaCheckDouble, FaCircle, FaClipboardCheck,
  FaClipboardList, FaCog, FaEdit, FaExternalLinkAlt, FaFileAlt,
  FaFileSignature, FaGraduationCap, FaIdBadge, FaIdCard, FaLayerGroup,
  FaSignOutAlt, FaThLarge, FaUserCheck, FaUserFriends, FaUserTie, FaUsers,
} from "react-icons/fa";
import type { IconType } from "react-icons";

export const ICONS: Record<string, IconType> = {
  FaBriefcase, FaBuilding, FaBullhorn, FaCalendarAlt, FaChartBar,
  FaCheckDouble, FaCircle, FaClipboardCheck, FaClipboardList, FaCog,
  FaExternalLinkAlt, FaFileAlt, FaFileSignature, FaGraduationCap, FaIdBadge,
  FaIdCard, FaLayerGroup, FaSignOutAlt, FaThLarge, FaUserCheck, FaUserFriends,
  FaUserTie, FaUsers, FaBalanceScale, FaCalendarCheck, FaEdit,

  // Phosphor / Server aliases used in ELM and Fusion modules
  CalendarBlank: FaCalendarAlt,
  PencilSimple: FaEdit,
  ListChecks: FaClipboardList,
  Scales: FaBalanceScale,
  UserSwitch: FaUserFriends,
  CalendarCheck: FaCalendarCheck,
  Gear: FaCog,
  FileText: FaFileAlt,
};

export type IconKey = keyof typeof ICONS;

export function resolveIcon(key: string | undefined): IconType {
  return (key && ICONS[key]) || FaCircle;
}
