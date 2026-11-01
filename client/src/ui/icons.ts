/** Icons cross the wire as strings ("FaBriefcase"), so the server can name one
 *  without the client shipping every icon in the set.
 *
 *  Named imports ONLY. `import * as Fa` defeats tree-shaking and ships ~1 MB. */
import {
  FaArchive,
  FaBriefcase, FaBuilding, FaBullhorn, FaCalendarAlt, FaChartBar,
  FaCheckCircle, FaCheckDouble, FaCircle, FaClipboardCheck, FaClipboardList, FaCog,
  FaCogs, FaDownload, FaExclamationTriangle, FaExchangeAlt,
  FaExternalLinkAlt, FaFileUpload,
  FaFileSignature, FaGraduationCap, FaHistory, FaIdBadge, FaIdCard, FaKey, FaLayerGroup,
  FaSignOutAlt, FaSync, FaTachometerAlt, FaThLarge, FaTimesCircle, FaTrashAlt,
  FaUserCheck, FaUserLock, FaUserMinus, FaUserPlus, FaUserShield, FaUserTie, FaUsers,
} from "react-icons/fa";
import type { IconType } from "react-icons";

export const ICONS = {
  FaArchive,
  FaBriefcase, FaBuilding, FaBullhorn, FaCalendarAlt, FaChartBar,
  FaCheckCircle, FaCheckDouble, FaCircle, FaClipboardCheck, FaClipboardList, FaCog,
  FaCogs, FaDownload, FaExclamationTriangle, FaExchangeAlt,
  FaExternalLinkAlt, FaFileUpload,
  FaFileSignature, FaGraduationCap, FaHistory, FaIdBadge, FaIdCard, FaKey, FaLayerGroup,
  FaSignOutAlt, FaSync, FaTachometerAlt, FaThLarge, FaTimesCircle, FaTrashAlt,
  FaUserCheck, FaUserLock, FaUserMinus, FaUserPlus, FaUserShield, FaUserTie, FaUsers,
} as const;

export type IconKey = keyof typeof ICONS;

export function resolveIcon(key: string | undefined): IconType {
  return (key && (ICONS as Record<string, IconType>)[key]) || FaCircle;
}
