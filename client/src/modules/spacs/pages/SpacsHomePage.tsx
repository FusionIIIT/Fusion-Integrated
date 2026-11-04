
import { Link } from "react-router-dom";

const sections = [
  {
    title: "Scholarship Catalogue",
    description: "Browse available scholarships, schemes and eligibility policies.",
    path: "catalogue",
  },
  {
    title: "My Applications",
    description: "View and manage your scholarship applications.",
    path: "mine",
  },
  {
    title: "Verification Queue",
    description: "Review submitted applications and supporting documents.",
    path: "verification",
  },
  {
    title: "Decision Queue",
    description: "Review applications and record scholarship decisions.",
    path: "decisions",
  },
  {
    title: "Award Management",
    description: "Manage convocation award cycles and results.",
    path: "awards",
  },
  {
    title: "Award Evaluation",
    description: "Evaluate eligible candidates and record recommendations.",
    path: "evaluation",
  },
  {
    title: "Catalogue Administration",
    description: "Manage scholarship catalogue entries and policy versions.",
    path: "admin",
  },
  {
    title: "Audit Trail",
    description: "Inspect recorded SPACS activities.",
    path: "audit",
  },
];

export default function SpacsHomePage() {
  return (
    <main style={{ padding: "28px", maxWidth: "1100px", margin: "0 auto" }}>
      <h1>Scholarships, Prizes and Awards</h1>
      <p>
        SPACS provides a centralized portal for scholarship applications,
        verification, decisions and convocation awards.
      </p>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(230px, 1fr))",
          gap: "18px",
          marginTop: "28px",
        }}
      >
        {sections.map((section) => (
          <Link
            key={section.path}
            to={section.path}
            style={{
              display: "block",
              padding: "20px",
              border: "1px solid #ddd",
              borderRadius: "10px",
              color: "inherit",
              textDecoration: "none",
            }}
          >
            <h3>{section.title}</h3>
            <p>{section.description}</p>
            <span>Open section →</span>
          </Link>
        ))}
      </div>
    </main>
  );
}
