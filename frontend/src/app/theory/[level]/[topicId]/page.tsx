import Link from "next/link";
import { notFound } from "next/navigation";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { completeTopic } from "@/app/actions";
import Icon from "@/components/Icon";
import { api } from "@/lib/api";
import { getT } from "@/lib/i18n/server";

export default async function TopicPage({ params }: { params: Promise<{ level: string; topicId: string }> }) {
  const { level, topicId } = await params;
  const id = Number(topicId);
  const [t, topic] = await Promise.all([getT(), Number.isInteger(id) ? api.topic(id) : null]);
  if (!topic || topic.level !== level) notFound();

  return (
    <div className="page narrow">
      <p>
        <Link href={`/theory/${level}`} className="back-link">
          <Icon name="arrow_back" />
          {t("theory.levelTitle", { level })}
        </Link>
      </p>
      <h1>{topic.title}</h1>
      <p className="subtitle">
        {t("theory.lessonMeta", { level: topic.level, n: topic.order_index })}{" "}
        {topic.is_completed && <span className="badge done">✓ {t("common.completed")}</span>}
      </p>

      <article className="lesson">
        <Markdown remarkPlugins={[remarkGfm]}>{topic.content}</Markdown>
      </article>

      <h2>{t("theory.vocabulary")}</h2>
      <div className="panel table-panel">
        <table className="data">
          <tbody>
            {topic.cards.map((c) => (
              <tr key={c.id}>
                <td>
                  <strong>{c.spanish}</strong>
                </td>
                <td>{c.english}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="actions">
        <Link href={`/quizzes?topic=${topic.id}`} className="button">
          <Icon name="play_arrow" filled />
          {t("theory.startPractice")}
        </Link>
        {!topic.is_completed && (
          <form action={completeTopic.bind(null, topic.id)}>
            <button className="secondary">
              <Icon name="check" />
              {t("theory.markRead")}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
