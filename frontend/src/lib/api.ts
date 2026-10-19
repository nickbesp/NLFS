// Server-side client for the FastAPI backend. Only runs on the Next.js server,
// so the browser never talks to FastAPI directly.
import "server-only";

import { connection } from "next/server";

import type { Card, HistoryEntry, Quiz, QuizAnswer, QuizResult, Stats, TopicDetail, TopicSummary } from "./types";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

class NotFound extends Error {}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  await connection(); // always render at request time: data is live, never pre-rendered at build
  let res: Response;
  try {
    res = await fetch(`${BACKEND_URL}${path}`, {
      cache: "no-store",
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    throw new Error(`Cannot reach the NLFS backend at ${BACKEND_URL}. Is it running?`);
  }
  if (res.status === 404) throw new NotFound(path);
  if (!res.ok) throw new Error(`Backend returned ${res.status} for ${path}: ${await res.text()}`);
  return res.json() as Promise<T>;
}

/** Like request(), but resolves to null on 404 so pages can call notFound(). */
async function requestOrNull<T>(path: string): Promise<T | null> {
  try {
    return await request<T>(path);
  } catch (e) {
    if (e instanceof NotFound) return null;
    throw e;
  }
}

const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });

export const api = {
  stats: () => request<Stats>("/api/stats"),
  topics: (level?: string) =>
    request<TopicSummary[]>(`/api/theory/topics${level ? `?level=${encodeURIComponent(level)}` : ""}`),
  topic: (id: number) => requestOrNull<TopicDetail>(`/api/theory/topics/${id}`),
  completeTopic: (id: number) => post<TopicSummary>(`/api/theory/topics/${id}/complete`),
  dueCards: () => request<Card[]>("/api/srs/review"),
  reviewCard: (id: number, quality: number) => post(`/api/srs/review/${id}`, { quality }),
  generateQuiz: (topicId: number, count = 5) =>
    requestOrNull<Quiz>(`/api/quiz/generate?topic_id=${topicId}&count=${count}`),
  submitQuiz: (topicId: number, answers: QuizAnswer[]) =>
    post<QuizResult>("/api/quiz/submit", { topic_id: topicId, answers }),
  history: () => request<HistoryEntry[]>("/api/quiz/history"),
};
