// Mirrors backend/app/schemas.py

export const LEVELS = ["A1", "A2", "B1", "B2", "C1"] as const;

export type Card = {
  id: number;
  topic_id: number | null;
  spanish: string;
  english: string;
  category: string;
  notes: string | null;
};

export type TopicSummary = {
  id: number;
  level: string;
  title: string;
  is_completed: boolean;
  order_index: number;
};

export type TopicDetail = TopicSummary & {
  content: string;
  cards: Card[];
};

export type QuizQuestion = {
  card_id: number;
  prompt: string;
  options: string[];
};

export type Quiz = {
  topic_id: number;
  questions: QuizQuestion[];
};

export type QuizAnswer = { card_id: number; answer: string };

export type QuizResult = {
  score: number;
  total: number;
  results: { card_id: number; prompt: string; answer: string; expected: string; correct: boolean }[];
};

export type HistoryEntry = {
  id: number;
  topic_id: number | null;
  topic_title: string | null;
  taken_at: string;
  score: number;
  total: number;
};

export type Stats = {
  topics_total: number;
  topics_completed: number;
  cards_total: number;
  cards_due: number;
  quizzes_taken: number;
};
