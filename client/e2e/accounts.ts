// Synthetic fusion-dev.dump accounts. Global setup grants each one its `grants` in the IAM.
export const PASSWORD = process.env.E2E_PASSWORD ?? "fusion123";

export interface Account {
  username: string;
  role: string;
  grants: readonly string[];
}

export const ACCOUNTS = {
  student: { username: "stu00001", role: "ug_student", grants: [] },
  placementOfficer: {
    username: "stf00062", role: "placement_officer", grants: ["placement_officer"],
  },
  faculty: {
    username: "fac00001", role: "professor", grants: ["professor"],
  },
  ta: {
    username: "stu00002", role: "teaching_assistant", grants: ["teaching_assistant"],
  },
  observer: {
    username: "stf00001", role: "course_observer", grants: ["course_observer"],
  },
} as const satisfies Record<string, Account>;

export type AccountKey = keyof typeof ACCOUNTS;
