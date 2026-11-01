// client/src/modules/quiz/api.ts
import axios from 'axios';

const API_URL = '/api/v1/quiz/';

export async function fetchQuizzes(): Promise<QuizDTO[]> {
    const response = await axios.get<QuizDTO[]>(API_URL);
    return response.data;
}

export async function createQuiz(quiz: QuizDTO): Promise<void> {
    await axios.post(API_URL, quiz);
}

export async function fetchQuestions(): Promise<QuestionDTO[]> {
    const response = await axios.get<QuestionDTO[]>(API_URL + 'questions/');
    return response.data;
}

export async function createQuestion(question: QuestionDTO): Promise<void> {
    await axios.post(API_URL + 'questions/', question);
}
