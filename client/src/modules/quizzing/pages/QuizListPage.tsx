import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useQuizzes, quizApi } from "../api/hooks";

export function QuizListPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<"student" | "faculty">("student");
  const { quizzes, loading, refetch } = useQuizzes(mode);

  return (
    <div style={{ padding: "1.5rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <PageHeader title="Quizzing" subtitle="Course quizzes & evaluation" />
        <div style={{ display: "flex", gap: 8 }}>
          <button onClick={() => setMode(mode === "student" ? "faculty" : "student")} style={{ padding: "6px 12px", border: "1px solid #cbd5e1", borderRadius: 4, background: "#fff", cursor: "pointer" }}>
            Switch to {mode === "student" ? "Faculty" : "Student"} View
          </button>
          {mode === "faculty" && (
            <Link to="/quizzing/create" style={{ background: "#2563eb", color: "#fff", padding: "6px 12px", borderRadius: 4, textDecoration: "none", fontWeight: 600 }}>
              + Create Quiz
            </Link>
          )}
        </div>
      </div>

      {loading && <p>Loading...</p>}
      {!loading && (
        <table style={{ width: "100%", borderCollapse: "collapse", background: "#fff", border: "1px solid #e2e8f0" }}>
          <thead>
            <tr style={{ background: "#f8fafc", textAlign: "left", fontSize: 13, borderBottom: "1px solid #e2e8f0" }}>
              <th style={{ padding: 10 }}>Course</th>
              <th style={{ padding: 10 }}>Title</th>
              <th style={{ padding: 10 }}>Duration</th>
              <th style={{ padding: 10 }}>Status</th>
              <th style={{ padding: 10 }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {quizzes.map((q) => (
              <tr key={q.id} style={{ borderBottom: "1px solid #f1f5f9", fontSize: 14 }}>
                <td style={{ padding: 10, fontWeight: 600 }}>{q.course_code}</td>
                <td style={{ padding: 10 }}>{q.title}</td>
                <td style={{ padding: 10 }}>{q.duration_minutes}m</td>
                <td style={{ padding: 10 }}><StatusBadge status={q.status} /></td>
                <td style={{ padding: 10 }}>
                  {mode === "student" ? (
                    <button onClick={async () => { const a = await quizApi.startAttempt(q.id); navigate(`/quizzing/attempt/${a.id}`); }} style={{ background: "#16a34a", color: "#fff", border: "none", padding: "4px 8px", borderRadius: 4, cursor: "pointer" }}>
                      Take Quiz
                    </button>
                  ) : (
                    <div style={{ display: "flex", gap: 4 }}>
                      {q.status === "DRAFT" && <button onClick={async () => { await quizApi.publishQuiz(q.id); refetch(); }} style={{ padding: "4px 6px", background: "#2563eb", color: "#fff", border: "none", borderRadius: 4 }}>Publish</button>}
                      <Link to={`/quizzing/grading/${q.id}`} style={{ padding: "4px 6px", border: "1px solid #cbd5e1", borderRadius: 4, textDecoration: "none", color: "#334155" }}>Grade</Link>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
