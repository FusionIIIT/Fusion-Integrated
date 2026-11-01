// client/src/modules/quiz/types.ts
export interface QuizDTO {
    id: number;
    title: string;
    description: string;
    questions: QuestionDTO[];
    start_time: string | null;
    end_time: string | null;
}

export interface QuestionDTO {
    id: number;
    type: string;
    text: string;
    options: string[] | null;
    answer: string | null;
}
