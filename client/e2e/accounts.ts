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
  hrEmployee: { username: "stf00001", role: "staff", grants: [] },
  hrAdmin: { username: "stf00061", role: "hradmin", grants: ["hradmin"] },
  hrReviewer: { username: "fac00021", role: "HOD (CSE)", grants: ["HOD (CSE)"] },
  hrAuthority: { username: "stf00003", role: "Registrar", grants: ["Registrar"] },
  hrAccountant: { username: "stf00004", role: "Accounts Admin", grants: ["Accounts Admin"] },
  hrOtherAuthority: { username: "fac00050", role: "Director", grants: [
    "HOD (Design)", "HOD (ECE)", "HOD (Liberal Arts)", "HOD (ME)", "HOD (NS)", "Director",
  ] },
} as const satisfies Record<string, Account>;

export type AccountKey = keyof typeof ACCOUNTS;
