import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useQuizAttempt, quizApi } from "../api/hooks";

export function QuizAttemptPage() {
  const { attemptId } = useParams<{ attemptId: string }>();
  const navigate = useNavigate();
  const { attempt, loading, refetch } = useQuizAttempt(attemptId || "");
  const [activeIdx, setActiveIdx] = useState(0);
  const [answers, setAnswers] = useState<Record<string, any>>({});
  const [timeLeft, setTimeLeft] = useState<number | null>(null);

  useEffect(() => {
    if (attempt?.status === "IN_PROGRESS" && attempt.quiz_duration) {
      const remaining = Math.max(0, Math.floor((new Date(attempt.started_at).getTime() + attempt.quiz_duration * 60000 - Date.now()) / 1000));
      setTimeLeft(remaining);
    }
  }, [attempt]);

  useEffect(() => {
    if (timeLeft === null || timeLeft <= 0 || attempt?.status !== "IN_PROGRESS") return;
    const t = setInterval(() => {
      setTimeLeft((p) => {
        if (p !== null && p <= 1) {
          clearInterval(t);
          quizApi.submitAttempt(attemptId!, true).then(() => refetch());
          return 0;
        }
        return p !== null ? p - 1 : null;
      });
    }, 1000);
    return () => clearInterval(t);
  }, [timeLeft, attempt?.status]);

  useEffect(() => {
    if (!attemptId || attempt?.status !== "IN_PROGRESS") return;
    const onHide = () => document.hidden && quizApi.logIntegrity(attemptId, "TAB_SWITCH", "User switched tab");
    const onBlur = () => quizApi.logIntegrity(attemptId, "WINDOW_BLUR", "Window blur");
    document.addEventListener("visibilitychange", onHide);
    window.addEventListener("blur", onBlur);
    return () => {
      document.removeEventListener("visibilitychange", onHide);
      window.removeEventListener("blur", onBlur);
    };
  }, [attemptId, attempt?.status]);

  const selectChoice = (qid: string, choice: string) => {
    setAnswers((p) => ({ ...p, [qid]: { choice } }));
    if (attemptId) quizApi.saveAnswer(attemptId, qid, { choice });
  };

  if (loading) return <div style={{ padding: 24 }}>Loading...</div>;
  if (!attempt) return <div style={{ padding: 24 }}>Attempt not found</div>;
  if (attempt.status !== "IN_PROGRESS") {
    return (
      <div style={{ padding: 32, textAlign: "center" }}>
        <h2>Quiz Completed</h2>
        <p>Status: {attempt.status} | Total Score: {attempt.total_score}</p>
        <button onClick={() => navigate("/quizzing")} style={{ padding: "6px 12px", background: "#2563eb", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer" }}>Back to Quizzes</button>
      </div>
    );
  }

  const current = attempt.answers[activeIdx];
  return (
    <div style={{ padding: "1.5rem", maxWidth: 700, margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <PageHeader title={attempt.quiz_title || "Quiz"} subtitle={`Question ${activeIdx + 1} of ${attempt.answers.length}`} />
        {timeLeft !== null && <div style={{ fontSize: 18, fontWeight: 700, padding: 8, background: "#f1f5f9", borderRadius: 6 }}>⏱️ {Math.floor(timeLeft / 60)}:{(timeLeft % 60).toString().padStart(2, "0")}</div>}
      </div>

      {current && (
        <div style={{ background: "#fff", padding: 20, borderRadius: 8, border: "1px solid #e2e8f0", marginTop: 12 }}>
          <p style={{ fontSize: 16, marginBottom: 16 }}>{current.question_text || `Question #${activeIdx + 1}`}</p>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {["A", "B", "C", "D"].map((opt) => (
              <label key={opt} style={{ padding: 8, border: "1px solid #cbd5e1", borderRadius: 4, cursor: "pointer", background: answers[current.question]?.choice === opt ? "#eff6ff" : "#fff" }}>
                <input type="radio" name={current.question} checked={answers[current.question]?.choice === opt} onChange={() => selectChoice(current.question, opt)} /> Option {opt}
              </label>
            ))}
          </div>

          <div style={{ display: "flex", justifyContent: "space-between", marginTop: 20 }}>
            <button disabled={activeIdx === 0} onClick={() => setActiveIdx((p) => p - 1)} style={{ padding: "4px 10px" }}>Prev</button>
            {activeIdx < attempt.answers.length - 1 ? (
              <button onClick={() => setActiveIdx((p) => p + 1)} style={{ padding: "4px 10px", background: "#2563eb", color: "#fff", border: "none", borderRadius: 4 }}>Next</button>
            ) : (
              <button onClick={() => { if (window.confirm("Submit quiz?")) quizApi.submitAttempt(attemptId!).then(() => refetch()); }} style={{ padding: "6px 14px", background: "#16a34a", color: "#fff", border: "none", borderRadius: 4, fontWeight: 600 }}>Submit</button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
