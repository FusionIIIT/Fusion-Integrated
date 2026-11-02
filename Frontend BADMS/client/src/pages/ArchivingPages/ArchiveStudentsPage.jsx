import ArchivePanel from "./ArchivePanel";

const COLUMNS = [
  { key: "username", label: "Roll No." },
  { key: "full_name", label: "Name" },
  { key: "programme", label: "Programme" },
  { key: "discipline", label: "Discipline" },
  { key: "batch", label: "Batch" },
  { key: "category", label: "Category" },
];

const FILTERS = [
  { key: "programme", label: "Programme" },
  { key: "discipline", label: "Discipline" },
  { key: "batch", label: "Batch" },
  { key: "category", label: "Category" },
];

const ArchiveStudentsPage = () => (
  <ArchivePanel
    type="student"
    title="Archive Students"
    subtitle="Retire graduating or departed students — archived students can no longer log in, be promoted, or register for courses"
    columns={COLUMNS}
    filterKeys={FILTERS}
  />
);

export default ArchiveStudentsPage;
