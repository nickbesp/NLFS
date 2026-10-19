"""FastAPI application: route handlers for the NLFS prototype."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from sqlalchemy.orm import Session

from . import crud, database, models, schemas
from .ingest import ingest_materials
from .seed import seed_if_empty


@asynccontextmanager
async def lifespan(app: FastAPI):
    models.Base.metadata.create_all(database.engine)
    with database.SessionLocal() as db:
        seed_if_empty(db)
    yield


app = FastAPI(title="NLFS API", lifespan=lifespan)
DB = Depends(database.get_db)


def _topic_or_404(db: Session, topic_id: int) -> models.TheoryTopic:
    topic = crud.get_topic(db, topic_id)
    if topic is None:
        raise HTTPException(404, "Topic not found")
    return topic


def _card_or_404(db: Session, card_id: int) -> models.Flashcard:
    card = db.get(models.Flashcard, card_id)
    if card is None:
        raise HTTPException(404, "Card not found")
    return card


@app.get("/api/stats", response_model=schemas.Stats)
def get_stats(db: Session = DB):
    return crud.stats(db)


# ---------- Theory ----------


@app.post("/api/theory/ingest")
def ingest():
    try:
        return ingest_materials()
    except NotImplementedError as e:
        raise HTTPException(501, str(e))


@app.get("/api/theory/topics", response_model=list[schemas.TopicSummary])
def list_topics(level: str | None = None, db: Session = DB):
    return crud.list_topics(db, level)


@app.get("/api/theory/topics/{topic_id}", response_model=schemas.TopicDetail)
def get_topic(topic_id: int, db: Session = DB):
    return _topic_or_404(db, topic_id)


@app.post("/api/theory/topics/{topic_id}/complete", response_model=schemas.TopicSummary)
def complete_topic(topic_id: int, db: Session = DB):
    return crud.complete_topic(db, _topic_or_404(db, topic_id))


# ---------- Flashcards ----------


@app.get("/api/words", response_model=list[schemas.Card])
def list_words(topic_id: int | None = None, db: Session = DB):
    return crud.list_cards(db, topic_id)


@app.post("/api/words", response_model=schemas.Card, status_code=201)
def create_word(data: schemas.CardCreate, db: Session = DB):
    if crud.card_exists(db, data.spanish):
        raise HTTPException(409, "Word already exists")
    if data.topic_id is not None:
        _topic_or_404(db, data.topic_id)
    return crud.create_card(db, data)


@app.delete("/api/words/{card_id}", status_code=204)
def delete_word(card_id: int, db: Session = DB):
    crud.delete_card(db, _card_or_404(db, card_id))
    return Response(status_code=204)


# ---------- SRS ----------


@app.get("/api/srs/review", response_model=list[schemas.Card])
def due_for_review(db: Session = DB):
    return crud.due_cards(db)


@app.post("/api/srs/review/{card_id}", response_model=schemas.SrsOut)
def review(card_id: int, data: schemas.ReviewIn, db: Session = DB):
    return crud.review_card(db, _card_or_404(db, card_id), data.quality)


# ---------- Quizzes ----------


@app.get("/api/quiz/generate", response_model=schemas.Quiz)
def generate_quiz(topic_id: int, count: int = Query(5, ge=1, le=20), db: Session = DB):
    topic = _topic_or_404(db, topic_id)
    if not topic.cards:
        raise HTTPException(400, "Topic has no cards to quiz on")
    return crud.generate_quiz(db, topic, count)


@app.post("/api/quiz/submit", response_model=schemas.QuizResult)
def submit_quiz(data: schemas.QuizSubmit, db: Session = DB):
    topic = _topic_or_404(db, data.topic_id)
    try:
        return crud.submit_quiz(db, topic, data.answers)
    except KeyError as e:
        raise HTTPException(400, f"Unknown card id {e.args[0]}")


@app.get("/api/quiz/history", response_model=list[schemas.HistoryEntry])
def history(db: Session = DB):
    return crud.quiz_history(db)
