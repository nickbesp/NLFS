"use client";

import Link from "next/link";
import { useState, useTransition } from "react";

import { reviewCard } from "@/app/actions";
import { useT } from "@/components/I18nProvider";
import type { Card } from "@/lib/types";

const RATINGS = [0, 1, 2, 3, 4, 5];

export default function FlashcardReview({ cards: dueCards }: { cards: Card[] }) {
  const t = useT();
  // Freeze the session's cards: each review revalidates the page, and the reviewed card
  // drops out of the fresh due list, which would shift the list under `index` and skip cards.
  const [cards] = useState(dueCards);
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  if (index >= cards.length) {
    return (
      <>
        <div className="flashcard">{t("flash.finished")}</div>
        <div className="actions">
          <Link href="/" className="button">
            {t("common.backToDashboard")}
          </Link>
        </div>
      </>
    );
  }

  const card = cards[index];

  function rate(quality: number) {
    setError(null);
    startTransition(async () => {
      try {
        await reviewCard(card.id, quality);
        setFlipped(false);
        setIndex((i) => i + 1);
      } catch {
        setError(t("flash.saveError"));
      }
    });
  }

  return (
    <>
      <p className="hint">
        {t("flash.cardOf", { n: index + 1, total: cards.length })}
      </p>
      <div className="flashcard">
        <div>{card.spanish}</div>
        {flipped && <div className="back">{card.english}</div>}
      </div>

      {!flipped ? (
        <div className="actions">
          <button onClick={() => setFlipped(true)}>{t("flash.show")}</button>
        </div>
      ) : (
        <>
          <div className="ratings">
            {RATINGS.map((q) => (
              <button key={q} onClick={() => rate(q)} disabled={pending} className={q < 3 ? "secondary" : ""}>
                {q}
              </button>
            ))}
          </div>
          <p className="hint">{t("flash.ratingHint")}</p>
        </>
      )}
      {error && <p className="wrong">{error}</p>}
    </>
  );
}
