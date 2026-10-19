"use client";

import Link from "next/link";
import { useState, useTransition } from "react";

import { submitQuiz } from "@/app/actions";
import { useT } from "@/components/I18nProvider";
import type { Quiz, QuizResult } from "@/lib/types";

export default function QuizRunner({ quiz, backHref }: { quiz: Quiz; backHref: string }) {
  const t = useT();
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [result, setResult] = useState<QuizResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  const allAnswered = quiz.questions.every((q) => answers[q.card_id] !== undefined);

  function submit() {
    setError(null);
    startTransition(async () => {
      try {
        const payload = quiz.questions.map((q) => ({ card_id: q.card_id, answer: answers[q.card_id] }));
        setResult(await submitQuiz(quiz.topic_id, payload));
      } catch {
        setError(t("quiz.submitError"));
      }
    });
  }

  if (result) {
    return (
      <>
        <h2>{t("quiz.score", { score: result.score, total: result.total })}</h2>
        <ul className="list">
          {result.results.map((r) => (
            <li key={r.card_id}>
              <div>
                <span>
                  <strong>{r.prompt}</strong> — {r.expected}
                </span>
                {r.correct ? (
                  <span className="correct">✓</span>
                ) : (
                  <span className="wrong">✗ {t("quiz.youSaid", { answer: r.answer })}</span>
                )}
              </div>
            </li>
          ))}
        </ul>
        <p className="hint">{t("quiz.topicCompleted")}</p>
        <div className="actions">
          <Link href={backHref} className="button">
            {t("quiz.backToRoadmap")}
          </Link>
          <Link href="/flashcards" className="button secondary">
            {t("quiz.reviewFlashcards")}
          </Link>
        </div>
      </>
    );
  }

  return (
    <>
      {quiz.questions.map((q, i) => (
        <section key={q.card_id} className="question">
          <h3>
            {i + 1}. {q.prompt}
          </h3>
          <div className="options">
            {q.options.map((opt) => (
              <button
                key={opt}
                type="button"
                className={answers[q.card_id] === opt ? "selected" : ""}
                onClick={() => setAnswers((a) => ({ ...a, [q.card_id]: opt }))}
              >
                {opt}
              </button>
            ))}
          </div>
        </section>
      ))}
      {error && <p className="wrong">{error}</p>}
      <button onClick={submit} disabled={!allAnswered || pending}>
        {pending ? t("quiz.checking") : t("quiz.submit")}
      </button>
    </>
  );
}
