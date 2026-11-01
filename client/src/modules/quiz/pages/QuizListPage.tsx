// client/src/modules/quiz/pages/QuizListPage.tsx
import React, { useEffect, useState } from 'react';
import { useAuth } from 'client/src/auth/AuthProvider';
import { useNavigate } from 'react-router-dom';
import { QuizDTO } from 'client/src/modules/quiz/types';
import { fetchQuizzes } from 'client/src/modules/quiz/api';

const QuizListPage: React.FC = () => {
    const { status } = useAuth();
    const navigate = useNavigate();
    const [quizzes, setQuizzes] = useState<QuizDTO[]>([]);

    useEffect(() => {
        if (status === 'authenticated') {
            fetchQuizzes().then(setQuizzes);
        }
    }, [status]);

    if (status !== 'authenticated') {
        return <div>Please log in to view quizzes.</div>;
    }

    return (
        <div>
            <h1>Quiz List</h1>
            <ul>
                {quizzes.map(quiz => (
                    <li key={quiz.id}>
                        <a href={`/quiz/${quiz.id}`}>{quiz.title}</a>
                    </li>
                ))}
            </ul>
            <button onClick={() => navigate('/quiz/create')}>Create Quiz</button>
        </div>
    );
};

export default QuizListPage;
