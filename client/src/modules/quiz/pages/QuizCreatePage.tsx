// client/src/modules/quiz/pages/QuizCreatePage.tsx
import React, { useState } from 'react';
import { useAuth } from 'client/src/auth/AuthProvider';
import { useNavigate } from 'react-router-dom';
import { QuizDTO } from 'client/src/modules/quiz/types';
import { createQuiz } from 'client/src/modules/quiz/api';

const QuizCreatePage: React.FC = () => {
    const { status } = useAuth();
    const navigate = useNavigate();
    const [title, setTitle] = useState('');
    const [description, setDescription] = useState('');
    const [startTime, setStartTime] = useState('');
    const [endTime, setEndTime] = useState('');

    if (status !== 'authenticated') {
        return <div>Please log in to create quizzes.</div>;
    }

    const handleSubmit = async (event: React.FormEvent) => {
        event.preventDefault();
        const quiz: QuizDTO = {
            id: 0,
            title,
            description,
            questions: [],
            start_time: startTime,
            end_time: endTime,
        };
        await createQuiz(quiz);
        navigate('/quiz/list');
    };

    return (
        <div>
            <h1>Create Quiz</h1>
            <form onSubmit={handleSubmit}>
                <div>
                    <label>Title:</label>
                    <input type="text" value={title} onChange={e => setTitle(e.target.value)} required />
                </div>
                <div>
                    <label>Description:</label>
                    <textarea value={description} onChange={e => setDescription(e.target.value)} required />
                </div>
                <div>
                    <label>Start Time:</label>
                    <input type="datetime-local" value={startTime} onChange={e => setStartTime(e.target.value)} />
                </div>
                <div>
                    <label>End Time:</label>
                    <input type="datetime-local" value={endTime} onChange={e => setEndTime(e.target.value)} />
                </div>
                <button type="submit">Create Quiz</button>
            </form>
        </div>
    );
};

export default QuizCreatePage;
