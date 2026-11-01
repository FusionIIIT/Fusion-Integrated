const currentAcademicYear = () => {
  const now = new Date();
  return now.getMonth() + 1 >= 7 ? now.getFullYear() : now.getFullYear() - 1;
};

const yearRange = (back) => {
  const current = currentAcademicYear();
  return Array.from({ length: back + 1 }, (_, i) => current - i);
};

const PHD_DISCIPLINES = [
  "Computer Science and Engineering",
  "Electronics and Communication Engineering",
  "Mechanical Engineering",
  "Smart Manufacturing",
  "Design",
];

export const PROGRAMME_CONFIG = {
  ug: {
    key: "ug",
    label: "UG",
    programmeType: "ug",
    showSpecialization: false,
    programmeOptions: ["B.Tech", "B.Des"],
    disciplineMap: {
      "B.Tech": [
        "Computer Science and Engineering",
        "Electronics and Communication Engineering",
        "Mechanical Engineering",
        "Smart Manufacturing",
      ],
      "B.Des": ["Design"],
    },
    yearOptions: yearRange(3),
    batchNamePrefixes: ["B."],
  },
  pg: {
    key: "pg",
    label: "PG",
    programmeType: "pg",
    showSpecialization: true,
    programmeOptions: [
      "M.Tech AI & ML",
      "M.Tech Data Science",
      "M.Tech Communication and Signal Processing",
      "M.Tech Nanoelectronics and VLSI Design",
      "M.Tech Power & Control",
      "M.Tech Design",
      "M.Tech CAD/CAM",
      "M.Tech Manufacturing and Automation",
      "M.Des",
    ],
    disciplineMap: {
      "M.Tech AI & ML": ["Computer Science and Engineering"],
      "M.Tech Data Science": ["Computer Science and Engineering"],
      "M.Tech Communication and Signal Processing": ["Electronics and Communication Engineering"],
      "M.Tech Nanoelectronics and VLSI Design": ["Electronics and Communication Engineering"],
      "M.Tech Power & Control": ["Electronics and Communication Engineering"],
      "M.Tech Design": ["Mechanical Engineering"],
      "M.Tech CAD/CAM": ["Mechanical Engineering"],
      "M.Tech Manufacturing and Automation": ["Mechanical Engineering"],
      "M.Des": ["Design"],
    },
    yearOptions: yearRange(1),
    batchNamePrefixes: ["M."],
  },
  phd: {
    key: "phd",
    label: "PhD",
    programmeType: "phd",
    showSpecialization: true,
    programmeOptions: ["PhD (Odd)", "PhD (Even)"],
    disciplineMap: {
      "PhD (Odd)": PHD_DISCIPLINES,
      "PhD (Even)": PHD_DISCIPLINES,
    },
    yearOptions: yearRange(5),
    batchNamePrefixes: ["PhD", "Phd", "phd"],
  },
};

export const SPECIALIZATION_OPTIONS = [
  "AI & ML",
  "Data Science",
  "Communication and Signal Processing",
  "Nanoelectronics and VLSI Design",
  "Power & Control",
  "Design",
  "CAD/CAM",
  "Manufacturing and Automation",
  "Mechatronics",
];

export const categorizeBatch = (batchName) => {
  if (!batchName) return null;
  if (batchName.startsWith("B.")) return "ug";
  if (batchName.startsWith("M.")) return "pg";
  if (batchName.toLowerCase().includes("phd")) return "phd";
  return null;
};

export { currentAcademicYear };
