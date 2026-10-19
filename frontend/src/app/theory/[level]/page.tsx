import Link from "next/link";
import { notFound } from "next/navigation";

import Icon from "@/components/Icon";
import { api } from "@/lib/api";
import { getT } from "@/lib/i18n/server";
import { LEVELS } from "@/lib/types";

export default async function LevelTopics({ params }: { params: Promise<{ level: string }> }) {
  const { level } = await params;
  if (!(LEVELS as readonly string[]).includes(level)) notFound();

  const [t, topics] = await Promise.all([getT(), api.topics(level)]);

  return (
    <div className="page narrow">
      <p>
        <Link href="/theory" className="back-link">
          <Icon name="arrow_back" />
          {t("theory.allLevels")}
        </Link>
      </p>
      <h1>{t("theory.levelTitle", { level })}</h1>
      <p className="subtitle">{t("theory.roadmap")}</p>

      {topics.length === 0 ? (
        <p>{t("theory.noTopicsLevel")}</p>
      ) : (
        <ol className="list">
          {topics.map((topic) => (
            <li key={topic.id}>
              <Link href={`/theory/${level}/${topic.id}`}>
                <span>
                  {topic.order_index}. {topic.title}
                </span>
                <span className={`badge ${topic.is_completed ? "done" : ""}`}>
                  {topic.is_completed ? `✓ ${t("common.completed")}` : t("common.toDo")}
                </span>
              </Link>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
