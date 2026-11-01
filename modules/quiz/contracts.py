# modules/quiz/contracts.py
from typing import Dict, List, Optional

class QuestionDTO:
    id: int
    type: str
    text: str
    options: Optional[List[str]]
    answer: Optional[str]

class QuizDTO:
    id: int
    title: str
    description: str
    questions: List[QuestionDTO]
    start_time: Optional[str]
    end_time: Optional[str]
