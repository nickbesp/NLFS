import Link from "next/link";
import { notFound } from "next/navigation";

import Icon from "@/components/Icon";
import QuizRunner from "@/components/QuizRunner";
import { api } from "@/lib/api";
import { getT } from "@/lib/i18n/server";

export default async function QuizzesPage({ searchParams }: { searchParams: Promise<{ topic?: string }> }) {
  const [{ topic: topicParam }, t] = await Promise.all([searchParams, getT()]);

  if (topicParam === undefined) {
    const topics = await api.topics();
    return (
      <div className="page narrow">
        <h1>{t("quiz.title")}</h1>
        <p className="subtitle">{t("quiz.subtitle")}</p>
        {topics.length === 0 ? (
          <p>{t("quiz.noTopics")}</p>
        ) : (
          <ul className="list">
            {topics.map((topic) => (
              <li key={topic.id}>
                <Link href={`/quizzes?topic=${topic.id}`}>
                  <span>
                    <span className="badge">{topic.level}</span> {topic.title}
                  </span>
                  <span className={`badge ${topic.is_completed ? "done" : ""}`}>
                    {topic.is_completed ? "✓" : t("common.start")}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    );
  }

  const topicId = Number(topicParam);
  const [topic, quiz] = Number.isInteger(topicId)
    ? await Promise.all([api.topic(topicId), api.generateQuiz(topicId)])
    : [null, null];
  if (!topic || !quiz) notFound();

  return (
    <div className="page narrow">
      <p>
        <Link href={`/theory/${topic.level}/${topic.id}`} className="back-link">
          <Icon name="arrow_back" />
          {topic.title}
        </Link>
      </p>
      <h1>{t("quiz.practice", { topic: topic.title })}</h1>
      <p className="subtitle">{t("quiz.instructions")}</p>
      <QuizRunner key={topicId} quiz={quiz} backHref={`/theory/${topic.level}`} />
    </div>
  );
}
