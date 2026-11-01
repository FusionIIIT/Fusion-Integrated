import type { RouteObject } from "react-router-dom";

import QuizListPage from "./pages/QuizListPage";
import QuizCreatePage from "./pages/QuizCreatePage";
import QuestionListPage from "./pages/QuestionListPage";
import QuestionCreatePage from "./pages/QuestionCreatePage";

export const routes: RouteObject[] = [
    { path: "/quiz/list", element: <QuizListPage /> },
    { path: "/quiz/create", element: <QuizCreatePage /> },
    { path: "/quiz/questions/list", element: <QuestionListPage /> },
    { path: "/quiz/questions/create", element: <QuestionCreatePage /> },
];
