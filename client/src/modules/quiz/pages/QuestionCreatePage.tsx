// client/src/modules/quiz/pages/QuestionCreatePage.tsx
import React, { useState } from 'react';
import { useAuth } from 'client/src/auth/AuthProvider';
import { useNavigate } from 'react-router-dom';
import { QuestionDTO } from 'client/src/modules/quiz/types';
import { createQuestion } from 'client/src/modules/quiz/api';

const QuestionCreatePage: React.FC = () => {
    const { status } = useAuth();
    const navigate = useNavigate();
    const [type, setType] = useState('mcq');
    const [text, setText] = useState('');
    const [answer, setAnswer] = useState('');

    if (status !== 'authenticated') {
        return <div>Please log in to create questions.</div>;
    }

    const handleSubmit = async (event: React.FormEvent) => {
        event.preventDefault();
        const question: QuestionDTO = {
            id: 0,
            type,
            text,
            answer,
            quiz: { id: 0, title: '', description: '', questions: [], start_time: '', end_time: '' },
        };
        await createQuestion(question);
        navigate('/quiz/questions/list');
    };

    return (
        <div>
            <h1>Create Question</h1>
            <form onSubmit={handleSubmit}>
                <div>
                    <label>Type:</label>
                    <select value={type} onChange={e => setType(e.target.value)} required>
                        <option value="mcq">Multiple Choice</option>
                        <option value="multi_select">Multiple Select</option>
                        <option value="true_false">True/False</option>
                        <option value="fill_in_the_blank">Fill in the Blank</option>
                        <option value="short_answer">Short Answer</option>
                    </select>
                </div>
                <div>
                    <label>Text:</label>
                    <textarea value={text} onChange={e => setText(e.target.value)} required />
                </div>
                <div>
                    <label>Answer:</label>
                    <input type="text" value={answer} onChange={e => setAnswer(e.target.value)} required />
                </div>
                <button type="submit">Create Question</button>
            </form>
        </div>
    );
};

export default QuestionCreatePage;
