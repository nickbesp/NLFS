"""Pydantic request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Card(ORMModel):
    id: int
    topic_id: int | None
    spanish: str
    english: str
    category: str
    notes: str | None


class CardCreate(BaseModel):
    spanish: str = Field(min_length=1)
    english: str = Field(min_length=1)
    topic_id: int | None = None
    category: str = "general"
    notes: str | None = None


class TopicSummary(ORMModel):
    id: int
    level: str
    title: str
    is_completed: bool
    order_index: int


class TopicDetail(TopicSummary):
    content: str
    cards: list[Card]


class ReviewIn(BaseModel):
    quality: int = Field(ge=0, le=5)


class SrsOut(ORMModel):
    flashcard_id: int
    repetitions: int
    interval: int
    ease_factor: float
    next_review: datetime


class QuizQuestion(BaseModel):
    card_id: int
    prompt: str
    options: list[str]


class Quiz(BaseModel):
    topic_id: int
    questions: list[QuizQuestion]


class QuizAnswer(BaseModel):
    card_id: int
    answer: str


class QuizSubmit(BaseModel):
    topic_id: int
    answers: list[QuizAnswer] = Field(min_length=1)


class QuizResultItem(BaseModel):
    card_id: int
    prompt: str
    answer: str
    expected: str
    correct: bool


class QuizResult(BaseModel):
    score: int
    total: int
    results: list[QuizResultItem]


class HistoryEntry(BaseModel):
    id: int
    topic_id: int | None
    topic_title: str | None
    taken_at: datetime
    score: int
    total: int


class Stats(BaseModel):
    topics_total: int
    topics_completed: int
    cards_total: int
    cards_due: int
    quizzes_taken: int
