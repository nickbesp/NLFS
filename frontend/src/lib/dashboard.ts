// Numbers the dashboard derives from existing API data. Pure, so it runs under plain Node tests.
import { LEVELS, type HistoryEntry, type TopicSummary } from "./types.ts";

const levelRank = (level: string) => {
  const i = (LEVELS as readonly string[]).indexOf(level);
  return i === -1 ? LEVELS.length : i;
};

/** The first uncompleted topic: lowest CEFR level first, then lesson order. */
export function nextTopic(topics: TopicSummary[]): TopicSummary | null {
  const todo = topics
    .filter((t) => !t.is_completed)
    .sort((a, b) => levelRank(a.level) - levelRank(b.level) || a.order_index - b.order_index);
  return todo[0] ?? null;
}

export function levelProgress(topics: TopicSummary[], level: string): { done: number; total: number; percent: number } {
  const inLevel = topics.filter((t) => t.level === level);
  const done = inLevel.filter((t) => t.is_completed).length;
  const total = inLevel.length;
  return { done, total, percent: total === 0 ? 0 : Math.round((done / total) * 100) };
}

/** Mean of each quiz's score percentage, or null when there is nothing to average. */
export function averageAccuracy(history: HistoryEntry[]): number | null {
  const scored = history.filter((h) => h.total > 0);
  if (scored.length === 0) return null;
  const sum = scored.reduce((acc, h) => acc + h.score / h.total, 0);
  return Math.round((sum / scored.length) * 100);
}

/** Matches /api/quiz/generate's default count of 5, limited by how many cards the topic has. */
export function quizQuestionCount(cardCount: number): number {
  return Math.min(5, cardCount);
}
