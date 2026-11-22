import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { fetchQuiz, startAttempt, saveAttemptAnswer, recordViolation, submitAttempt } from "../api";
import type { Quiz, QuizAttempt, QuizQuestion } from "../types";

export default function QuizTakePage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [quiz, setQuiz] = useState<Quiz | null>(null);
  const [attempt, setAttempt] = useState<QuizAttempt | null>(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<number, any>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    const quizId = Number(id);
    Promise.all([fetchQuiz(quizId), startAttempt(quizId)])
      .then(([q, att]) => {
        setQuiz(q);
        setAttempt(att);
        const initialAnswers: Record<number, any> = {};
        att.responses?.forEach((r) => {
          initialAnswers[r.question_id] = r.answer;
        });
        setAnswers(initialAnswers);
      })
      .catch((err) => {
        alert(`Cannot start attempt: ${err.message}`);
        navigate("/quiz");
      })
      .finally(() => setLoading(false));
  }, [id, navigate]);

  // Tab switch violation detection
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.hidden && attempt && attempt.status === "STARTED") {
        recordViolation(attempt.id).then((res) => {
          if (res.status === "SUBMITTED") {
            alert("Maximum tab violation limit reached. Your attempt has been submitted.");
            navigate(`/quiz`);
          } else {
            alert(`Warning: Tab change detected! Total violations: ${res.tab_violations}`);
          }
        });
      }
    };
    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => document.removeEventListener("visibilitychange", handleVisibilityChange);
  }, [attempt, navigate]);

  const handleSelectOption = (qid: number, optId: string) => {
    setAnswers((prev) => ({ ...prev, [qid]: optId }));
    if (attempt) {
      saveAttemptAnswer(attempt.id, qid, optId).catch(console.error);
    }
  };

  const handleSubmit = async () => {
    if (!attempt || !quiz) return;
    const answeredCount = Object.keys(answers).length;
    const total = quiz.questions?.length || 0;
    const ok = window.confirm(`You have answered ${answeredCount} of ${total} questions. Are you sure you want to submit?`);
    if (!ok) return;

    try {
      await submitAttempt(attempt.id);
      alert("Quiz attempt submitted successfully!");
      navigate("/quiz");
    } catch (err: any) {
      alert(`Submission failed: ${err.message}`);
    }
  };

  if (loading || !quiz || !attempt) return <div className="p-6">Preparing quiz attempt...</div>;

  const questions: QuizQuestion[] = quiz.questions || [];
  const currentQ = questions[currentIndex];

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <div className="flex justify-between items-center bg-gray-50 p-4 rounded border">
        <div>
          <h1 className="text-xl font-bold">{quiz.title}</h1>
          <p className="text-xs text-gray-500">Attempt ID: #{attempt.id}</p>
        </div>
        <button
          onClick={handleSubmit}
          className="bg-red-600 text-white px-4 py-2 rounded font-semibold hover:bg-red-700"
        >
          Submit Quiz
        </button>
      </div>

      {currentQ && (
        <div className="bg-white p-6 rounded-lg border shadow space-y-4">
          <div className="flex justify-between text-sm text-gray-500">
            <span>Question {currentIndex + 1} of {questions.length}</span>
            <span>{currentQ.marks} Marks</span>
          </div>
          <h2 className="text-lg font-medium text-gray-900">{currentQ.question_text}</h2>

          <div className="space-y-2 pt-2">
            {currentQ.options?.map((opt) => (
              <label
                key={opt.option_id}
                className="flex items-center space-x-3 p-3 rounded border hover:bg-gray-50 cursor-pointer"
              >
                <input
                  type="radio"
                  name={`question-${currentQ.id}`}
                  checked={answers[currentQ.id] === opt.option_text}
                  onChange={() => handleSelectOption(currentQ.id, opt.option_text)}
                  className="h-4 w-4 text-blue-600"
                />
                <span className="text-gray-800">{opt.option_text}</span>
              </label>
            ))}
          </div>

          <div className="flex justify-between pt-6 border-t">
            <button
              disabled={currentIndex === 0}
              onClick={() => setCurrentIndex((i) => i - 1)}
              className="px-4 py-2 border rounded disabled:opacity-50"
            >
              Previous
            </button>
            <button
              disabled={currentIndex === questions.length - 1}
              onClick={() => setCurrentIndex((i) => i + 1)}
              className="px-4 py-2 bg-blue-600 text-white rounded disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
