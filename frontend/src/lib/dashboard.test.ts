import assert from "node:assert/strict";
import { test } from "node:test";

import { averageAccuracy, levelProgress, nextTopic, quizQuestionCount } from "./dashboard.ts";
import type { HistoryEntry, TopicSummary } from "./types.ts";

const topic = (id: number, level: string, order_index: number, is_completed = false): TopicSummary => ({
  id,
  level,
  title: `T${id}`,
  order_index,
  is_completed,
});

const quiz = (score: number, total: number): HistoryEntry => ({
  id: score * 100 + total,
  topic_id: 1,
  topic_title: "T1",
  taken_at: "2026-10-16T10:00:00",
  score,
  total,
});

test("nextTopic picks the lowest level first, then the lesson order", () => {
  const topics = [topic(3, "B1", 1), topic(2, "A1", 2), topic(1, "A1", 1, true)];
  assert.equal(nextTopic(topics)?.id, 2);
});

test("nextTopic returns null when every topic is completed", () => {
  assert.equal(nextTopic([topic(1, "A1", 1, true)]), null);
});

test("nextTopic returns null when there are no topics", () => {
  assert.equal(nextTopic([]), null);
});

test("levelProgress counts only the given level and rounds the percent", () => {
  const topics = [topic(1, "A1", 1, true), topic(2, "A1", 2, true), topic(3, "A1", 3), topic(4, "A2", 1, true)];
  assert.deepEqual(levelProgress(topics, "A1"), { done: 2, total: 3, percent: 67 });
});

test("levelProgress is zero for a level with no topics", () => {
  assert.deepEqual(levelProgress([], "C1"), { done: 0, total: 0, percent: 0 });
});

test("averageAccuracy is null without any quiz history", () => {
  assert.equal(averageAccuracy([]), null);
});

test("averageAccuracy averages each quiz's percentage", () => {
  assert.equal(averageAccuracy([quiz(4, 5), quiz(3, 5)]), 70);
});

test("averageAccuracy skips quizzes with zero questions", () => {
  assert.equal(averageAccuracy([quiz(0, 0), quiz(5, 5)]), 100);
});

test("quizQuestionCount caps at five and follows small decks", () => {
  assert.equal(quizQuestionCount(3), 3);
  assert.equal(quizQuestionCount(12), 5);
  assert.equal(quizQuestionCount(0), 0);
});
