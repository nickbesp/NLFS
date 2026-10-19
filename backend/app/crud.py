"""Database helpers used by the route handlers."""

import json
import random
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import models, schemas
from .database import utcnow
from .srs import sm2

# ---------- Theory ----------


def list_topics(db: Session, level: str | None = None) -> list[models.TheoryTopic]:
    stmt = select(models.TheoryTopic).order_by(models.TheoryTopic.level, models.TheoryTopic.order_index)
    if level:
        stmt = stmt.where(models.TheoryTopic.level == level.upper())
    return list(db.scalars(stmt))


def get_topic(db: Session, topic_id: int) -> models.TheoryTopic | None:
    return db.get(models.TheoryTopic, topic_id)


def complete_topic(db: Session, topic: models.TheoryTopic) -> models.TheoryTopic:
    topic.is_completed = True
    db.commit()
    return topic


# ---------- Flashcards ----------


def list_cards(db: Session, topic_id: int | None = None) -> list[models.Flashcard]:
    stmt = select(models.Flashcard).order_by(models.Flashcard.id)
    if topic_id is not None:
        stmt = stmt.where(models.Flashcard.topic_id == topic_id)
    return list(db.scalars(stmt))


def card_exists(db: Session, spanish: str) -> bool:
    return db.scalar(select(models.Flashcard.id).where(models.Flashcard.spanish == spanish)) is not None


def create_card(db: Session, data: schemas.CardCreate) -> models.Flashcard:
    card = models.Flashcard(**data.model_dump(), srs=models.SrsState())
    db.add(card)
    db.commit()
    return card


def delete_card(db: Session, card: models.Flashcard) -> None:
    db.delete(card)
    db.commit()


# ---------- SRS ----------


def due_cards(db: Session) -> list[models.Flashcard]:
    stmt = (
        select(models.Flashcard)
        .join(models.SrsState)
        .where(models.SrsState.next_review <= utcnow())
        .order_by(models.SrsState.next_review, models.Flashcard.id)
    )
    return list(db.scalars(stmt))


def review_card(db: Session, card: models.Flashcard, quality: int) -> models.SrsState:
    state = card.srs
    state.repetitions, state.interval, state.ease_factor = sm2(
        state.repetitions, state.interval, state.ease_factor, quality
    )
    now = utcnow()
    state.last_reviewed = now
    state.next_review = now + timedelta(days=state.interval)
    db.commit()
    return state


# ---------- Quizzes ----------


def generate_quiz(db: Session, topic: models.TheoryTopic, count: int) -> schemas.Quiz:
    cards = random.sample(topic.cards, min(count, len(topic.cards)))
    all_english = {c.english for c in list_cards(db)}
    questions = []
    for card in cards:
        distractors = random.sample(sorted(all_english - {card.english}), 3)
        options = [card.english, *distractors]
        random.shuffle(options)
        questions.append(schemas.QuizQuestion(card_id=card.id, prompt=card.spanish, options=options))
    return schemas.Quiz(topic_id=topic.id, questions=questions)


def submit_quiz(db: Session, topic: models.TheoryTopic, answers: list[schemas.QuizAnswer]) -> schemas.QuizResult:
    """Grade answers, log them to quiz_history and mark the topic completed.

    Raises KeyError if an answer references an unknown card.
    """
    results = []
    for a in answers:
        card = db.get(models.Flashcard, a.card_id)
        if card is None:
            raise KeyError(a.card_id)
        results.append(
            schemas.QuizResultItem(
                card_id=card.id,
                prompt=card.spanish,
                answer=a.answer,
                expected=card.english,
                correct=a.answer.strip().casefold() == card.english.casefold(),
            )
        )
    score = sum(r.correct for r in results)
    db.add(
        models.QuizHistory(
            topic_id=topic.id,
            score=score,
            total=len(results),
            details=json.dumps([r.model_dump() for r in results], ensure_ascii=False),
        )
    )
    topic.is_completed = True
    db.commit()
    return schemas.QuizResult(score=score, total=len(results), results=results)


def quiz_history(db: Session) -> list[schemas.HistoryEntry]:
    rows = db.scalars(select(models.QuizHistory).order_by(models.QuizHistory.taken_at.desc()))
    return [
        schemas.HistoryEntry(
            id=h.id,
            topic_id=h.topic_id,
            topic_title=h.topic.title if h.topic else None,
            taken_at=h.taken_at,
            score=h.score,
            total=h.total,
        )
        for h in rows
    ]


# ---------- Stats ----------


def stats(db: Session) -> schemas.Stats:
    count = lambda stmt: db.scalar(stmt) or 0  # noqa: E731
    return schemas.Stats(
        topics_total=count(select(func.count(models.TheoryTopic.id))),
        topics_completed=count(select(func.count(models.TheoryTopic.id)).where(models.TheoryTopic.is_completed)),
        cards_total=count(select(func.count(models.Flashcard.id))),
        cards_due=count(select(func.count(models.SrsState.id)).where(models.SrsState.next_review <= utcnow())),
        quizzes_taken=count(select(func.count(models.QuizHistory.id))),
    )
