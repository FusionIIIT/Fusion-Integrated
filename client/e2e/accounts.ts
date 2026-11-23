// Synthetic fusion-dev.dump accounts. Global setup grants each one its `grants` in the IAM.
export const PASSWORD = process.env.E2E_PASSWORD ?? "fusion123";

export interface Account {
  username: string;
  role: string;
  grants: readonly string[];
}

export const ACCOUNTS = {
  lmsNoCourse: { username: "stf00003", role: "placement_officer", grants: ["placement_officer"] },
  lmsFaculty: { username: "fac00021", role: "faculty", grants: [] },
  lmsStudent: { username: "stu03009", role: "student", grants: [] },
  lmsTa: { username: "stu03008", role: "lms_ta", grants: ["lms_ta"] },
  lmsObserver: { username: "stf00001", role: "lms_observer", grants: ["lms_observer"] },
  lmsPlain: { username: "stu00001", role: "student", grants: [] },
  student: { username: "stu00001", role: "ug_student", grants: [] },
  placementOfficer: {
    username: "stf00062", role: "placement_officer", grants: ["placement_officer"],
  },
} as const satisfies Record<string, Account>;

export type AccountKey = keyof typeof ACCOUNTS;
