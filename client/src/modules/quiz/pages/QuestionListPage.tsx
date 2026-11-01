// client/src/modules/quiz/pages/QuestionListPage.tsx
import React, { useEffect, useState } from 'react';
import { useAuth } from 'client/src/auth/AuthProvider';
import { useNavigate } from 'react-router-dom';
import { QuestionDTO } from 'client/src/modules/quiz/types';
import { fetchQuestions } from 'client/src/modules/quiz/api';

const QuestionListPage: React.FC = () => {
    const { status } = useAuth();
    const navigate = useNavigate();
    const [questions, setQuestions] = useState<QuestionDTO[]>([]);

    useEffect(() => {
        if (status === 'authenticated') {
            fetchQuestions().then(setQuestions);
        }
    }, [status]);

    if (status !== 'authenticated') {
        return <div>Please log in to view questions.</div>;
    }

    return (
        <div>
            <h1>Question List</h1>
            <ul>
                {questions.map(question => (
                    <li key={question.id}>
                        <a href={`/quiz/questions/${question.id}`}>{question.text}</a>
                    </li>
                ))}
            </ul>
            <button onClick={() => navigate('/quiz/questions/create')}>Create Question</button>
        </div>
    );
};

export default QuestionListPage;
