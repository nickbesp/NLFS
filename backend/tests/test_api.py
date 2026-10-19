def test_seeded_on_startup(client):
    stats = client.get("/api/stats").json()
    assert stats["topics_total"] == 5
    assert stats["topics_completed"] == 0
    assert stats["cards_total"] > 0
    assert stats["cards_due"] == stats["cards_total"]
    assert stats["quizzes_taken"] == 0


def test_topics_filtered_by_level_and_ordered(client):
    topics = client.get("/api/theory/topics", params={"level": "A1"}).json()
    assert len(topics) == 3
    assert [t["order_index"] for t in topics] == sorted(t["order_index"] for t in topics)
    assert "content" not in topics[0]


def test_topic_detail_includes_content_and_cards(client):
    topic_id = client.get("/api/theory/topics").json()[0]["id"]
    topic = client.get(f"/api/theory/topics/{topic_id}").json()
    assert topic["content"]
    assert len(topic["cards"]) >= 5


def test_unknown_topic_is_404(client):
    assert client.get("/api/theory/topics/9999").status_code == 404


def test_mark_topic_complete(client):
    topic_id = client.get("/api/theory/topics").json()[0]["id"]
    res = client.post(f"/api/theory/topics/{topic_id}/complete")
    assert res.status_code == 200
    assert res.json()["is_completed"] is True


def test_quiz_round_trip_marks_topic_complete_and_logs_history(client):
    topic_id = client.get("/api/theory/topics").json()[0]["id"]
    quiz = client.get("/api/quiz/generate", params={"topic_id": topic_id, "count": 5}).json()
    assert len(quiz["questions"]) == 5
    for q in quiz["questions"]:
        assert len(q["options"]) == 4
        assert "answer" not in q

    english_by_id = {c["id"]: c["english"] for c in client.get("/api/words", params={"topic_id": topic_id}).json()}
    answers = [{"card_id": q["card_id"], "answer": english_by_id[q["card_id"]]} for q in quiz["questions"]]
    answers[0]["answer"] = "definitely wrong"

    result = client.post("/api/quiz/submit", json={"topic_id": topic_id, "answers": answers}).json()
    assert (result["score"], result["total"]) == (4, 5)
    assert result["results"][0]["correct"] is False
    assert result["results"][0]["expected"] == english_by_id[answers[0]["card_id"]]

    assert client.get(f"/api/theory/topics/{topic_id}").json()["is_completed"] is True
    history = client.get("/api/quiz/history").json()
    assert len(history) == 1
    assert history[0]["score"] == 4
    assert history[0]["topic_title"]


def test_srs_review_reschedules_card(client):
    due = client.get("/api/srs/review").json()
    card_id = due[0]["id"]
    res = client.post(f"/api/srs/review/{card_id}", json={"quality": 4})
    assert res.status_code == 200
    assert res.json()["interval"] == 1
    assert card_id not in [c["id"] for c in client.get("/api/srs/review").json()]


def test_srs_review_rejects_bad_quality(client):
    card_id = client.get("/api/srs/review").json()[0]["id"]
    assert client.post(f"/api/srs/review/{card_id}", json={"quality": 7}).status_code == 422


def test_words_create_and_delete(client):
    res = client.post("/api/words", json={"spanish": "el gato", "english": "the cat"})
    assert res.status_code == 201
    card_id = res.json()["id"]
    assert card_id in [c["id"] for c in client.get("/api/srs/review").json()]
    assert client.delete(f"/api/words/{card_id}").status_code == 204
    assert client.delete(f"/api/words/{card_id}").status_code == 404


def test_duplicate_word_rejected(client):
    first = client.get("/api/words").json()[0]
    res = client.post("/api/words", json={"spanish": first["spanish"], "english": "x"})
    assert res.status_code == 409


def test_ingest_is_stubbed(client):
    assert client.post("/api/theory/ingest").status_code == 501
