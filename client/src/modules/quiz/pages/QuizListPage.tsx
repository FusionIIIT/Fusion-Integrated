import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchQuizzes } from "../api";
import type { Quiz } from "../types";

export default function QuizListPage() {
  const [quizzes, setQuizzes] = useState<Quiz[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchQuizzes()
      .then((data) => setQuizzes(data))
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-4">Loading quizzes...</div>;

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Quiz Management</h1>
        <Link
          to="/quiz/create"
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          Create Quiz
        </Link>
      </div>

      <div className="bg-white shadow rounded-lg overflow-hidden border">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Title</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Course</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Duration</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {quizzes.map((quiz) => (
              <tr key={quiz.id}>
                <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">{quiz.title}</td>
                <td className="px-6 py-4 whitespace-nowrap text-gray-500">Course #{quiz.course_id}</td>
                <td className="px-6 py-4 whitespace-nowrap text-gray-500">{quiz.duration_minutes} mins</td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`px-2 py-1 text-xs font-semibold rounded ${
                    quiz.status === "AVAILABLE" ? "bg-green-100 text-green-800" :
                    quiz.status === "DRAFT" ? "bg-yellow-100 text-yellow-800" : "bg-gray-100 text-gray-800"
                  }`}>
                    {quiz.status}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm space-x-2">
                  <Link to={`/quiz/${quiz.id}`} className="text-blue-600 hover:underline">
                    View
                  </Link>
                  {quiz.status === "AVAILABLE" && (
                    <Link to={`/quiz/${quiz.id}/take`} className="text-green-600 hover:underline font-semibold">
                      Attempt
                    </Link>
                  )}
                </td>
              </tr>
            ))}
            {quizzes.length === 0 && (
              <tr>
                <td colSpan={5} className="px-6 py-8 text-center text-gray-500">
                  No quizzes available.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
