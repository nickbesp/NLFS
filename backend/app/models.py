"""SQLAlchemy models mirroring the schema in research/nlfs-plan.md."""

from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base, utcnow


class TheoryTopic(Base):
    __tablename__ = "theory_topics"

    id: Mapped[int] = mapped_column(primary_key=True)
    level: Mapped[str] = mapped_column(String(2), index=True)
    title: Mapped[str]
    content: Mapped[str] = mapped_column(Text)
    is_completed: Mapped[bool] = mapped_column(default=False)
    order_index: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    cards: Mapped[list["Flashcard"]] = relationship(back_populates="topic", order_by="Flashcard.id")


class Flashcard(Base):
    __tablename__ = "flashcards"

    id: Mapped[int] = mapped_column(primary_key=True)
    topic_id: Mapped[int | None] = mapped_column(ForeignKey("theory_topics.id", ondelete="SET NULL"))
    spanish: Mapped[str] = mapped_column(unique=True)
    english: Mapped[str]
    category: Mapped[str] = mapped_column(default="general")
    notes: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    topic: Mapped[TheoryTopic | None] = relationship(back_populates="cards")
    srs: Mapped["SrsState"] = relationship(back_populates="card", cascade="all, delete-orphan")


class SrsState(Base):
    __tablename__ = "srs_state"

    id: Mapped[int] = mapped_column(primary_key=True)
    flashcard_id: Mapped[int] = mapped_column(ForeignKey("flashcards.id", ondelete="CASCADE"), unique=True)
    repetitions: Mapped[int] = mapped_column(default=0)
    interval: Mapped[int] = mapped_column(default=1)
    ease_factor: Mapped[float] = mapped_column(default=2.5)
    next_review: Mapped[datetime] = mapped_column(default=utcnow, index=True)
    last_reviewed: Mapped[datetime | None]

    card: Mapped[Flashcard] = relationship(back_populates="srs")


class QuizHistory(Base):
    __tablename__ = "quiz_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    topic_id: Mapped[int | None] = mapped_column(ForeignKey("theory_topics.id", ondelete="SET NULL"))
    taken_at: Mapped[datetime] = mapped_column(default=utcnow)
    score: Mapped[int]
    total: Mapped[int]
    details: Mapped[str | None] = mapped_column(Text)  # JSON list of per-question results

    topic: Mapped[TheoryTopic | None] = relationship()
