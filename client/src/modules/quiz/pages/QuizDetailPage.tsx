import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { fetchQuiz, publishQuiz } from "../api";
import type { Quiz } from "../types";

export default function QuizDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [quiz, setQuiz] = useState<Quiz | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (id) {
      fetchQuiz(Number(id))
        .then((q) => setQuiz(q))
        .finally(() => setLoading(false));
    }
  }, [id]);

  const handlePublish = async () => {
    if (!quiz) return;
    try {
      const updated = await publishQuiz(quiz.id);
      setQuiz(updated);
      alert("Quiz published successfully!");
    } catch (e: any) {
      alert(`Error publishing: ${e.message}`);
    }
  };

  if (loading) return <div className="p-4">Loading quiz details...</div>;
  if (!quiz) return <div className="p-4">Quiz not found.</div>;

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold">{quiz.title}</h1>
          <p className="text-gray-500">Course #{quiz.course_id} • {quiz.duration_minutes} minutes</p>
        </div>
        <div className="space-x-2">
          {["DRAFT", "DRAFT_CONFIGURED", "READY_TO_PUBLISH"].includes(quiz.status) && (
            <button
              onClick={handlePublish}
              className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 font-medium"
            >
              Publish Quiz
            </button>
          )}
          <Link
            to="/quiz"
            className="border border-gray-300 px-4 py-2 rounded hover:bg-gray-50 text-gray-700"
          >
            Back
          </Link>
        </div>
      </div>

      <div className="bg-white p-6 rounded-lg border shadow space-y-4">
        <h2 className="text-lg font-semibold">Instructions</h2>
        <p className="text-gray-700 whitespace-pre-wrap">{quiz.instructions || "No instructions provided."}</p>
      </div>

      <div className="bg-white p-6 rounded-lg border shadow space-y-4">
        <h2 className="text-lg font-semibold">Questions ({quiz.questions?.length || 0})</h2>
        <div className="divide-y">
          {quiz.questions?.map((q, idx) => (
            <div key={q.id} className="py-3">
              <div className="flex justify-between">
                <span className="font-medium">Q{idx + 1}: {q.question_text}</span>
                <span className="text-sm text-gray-500">{q.marks} marks ({q.question_type})</span>
              </div>
            </div>
          ))}
          {(!quiz.questions || quiz.questions.length === 0) && (
            <p className="text-gray-500 py-2">No questions added yet.</p>
          )}
        </div>
      </div>
    </div>
  );
}
