import type { FileStatus } from "../api/types";

/** What the signed-in employee may do with a file. This only decides which
 *  buttons to show; the server enforces the same rules (BR-FTS-001, -007,
 *  -012) and its refusal is shown if the two ever disagree. */
export interface FileActions {
  canForward: boolean;
  canReturn: boolean;
  canArchive: boolean;
  readOnly: boolean;
}

interface Subject {
  status: FileStatus;
  creator_id: string;
  current_holder_id: string;
}

export function actionsFor(file: Subject, me: string | undefined): FileActions {
  const none = { canForward: false, canReturn: false, canArchive: false };
  if (file.status === "archived") return { ...none, readOnly: true };
  if (!me) return { ...none, readOnly: false };

  const holds = file.current_holder_id === me;
  const isDraft = file.status === "draft";
  return {
    // A draft is sent through the same Forward action (first circulation).
    canForward: holds,
    canReturn: holds && !isDraft,
    // The backend lets the creator or the current holder archive a circulated file.
    canArchive: !isDraft && (file.creator_id === me || holds),
    readOnly: false,
  };
}

export const STATUS_LABEL: Record<FileStatus, string> = {
  draft: "Draft",
  in_transit: "In transit",
  received: "Received",
  returned: "Returned",
  archived: "Archived",
};

export const STATUS_COLOR: Record<FileStatus, string> = {
  draft: "gray",
  in_transit: "blue",
  received: "teal",
  returned: "orange",
  archived: "dark",
};
