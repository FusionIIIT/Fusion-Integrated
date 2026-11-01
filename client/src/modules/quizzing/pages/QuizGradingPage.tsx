import React, { useState } from "react";
import { useParams } from "react-router-dom";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useQuizDetail, useQuizSubmissions, quizApi } from "../api/hooks";

export function QuizGradingPage() {
  const { quizId } = useParams<{ quizId: string }>();
  const { quiz, refetch: refetchQuiz } = useQuizDetail(quizId || "");
  const { submissions, loading, refetch: refetchSubs } = useQuizSubmissions(quizId || "");
  const [overrideScores, setOverrideScores] = useState<Record<string, number>>({});

  const toggleRelease = async (type: "key" | "grades") => {
    if (!quiz) return;
    const current = type === "key" ? quiz.answer_key_released : quiz.grades_released;
    await quizApi.toggleRelease(quiz.id, type, !current);
    refetchQuiz();
  };

  return (
    <div style={{ padding: "1.5rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <PageHeader title={`Grading: ${quiz?.title || ""}`} subtitle={`${submissions.length} Submissions`} />
        {quiz && (
          <div style={{ display: "flex", gap: 8 }}>
            <button onClick={() => toggleRelease("key")} style={{ padding: "4px 8px", border: "1px solid #cbd5e1", borderRadius: 4, background: quiz.answer_key_released ? "#dcfce7" : "#fff" }}>
              {quiz.answer_key_released ? "✓ Key Released" : "Release Key"}
            </button>
            <button onClick={() => toggleRelease("grades")} style={{ padding: "4px 8px", background: quiz.grades_released ? "#16a34a" : "#2563eb", color: "#fff", border: "none", borderRadius: 4 }}>
              {quiz.grades_released ? "✓ Grades Released" : "Release Grades"}
            </button>
          </div>
        )}
      </div>

      {loading && <p>Loading...</p>}
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {submissions.map((sub) => (
          <div key={sub.id} style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 6, padding: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
              <strong>{sub.student_user_id} ({sub.status})</strong>
              <span>Total: {sub.total_score}</span>
            </div>
            {sub.answers.map((a) => (
              <div key={a.id} style={{ display: "flex", justifyContent: "space-between", fontSize: 13, padding: "2px 0" }}>
                <span>{a.question_text || "Q"}: {JSON.stringify(a.submitted_answer)}</span>
                <div style={{ display: "flex", gap: 4 }}>
                  <span>Score: {a.final_score}</span>
                  <input type="number" step="0.5" defaultValue={a.final_score} onChange={(e) => setOverrideScores({ ...overrideScores, [a.id]: Number(e.target.value) })} style={{ width: 50 }} />
                  <button onClick={async () => { await quizApi.overrideScore(a.id, overrideScores[a.id]); refetchSubs(); }}>Save</button>
                </div>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
