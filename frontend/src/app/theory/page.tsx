import Link from "next/link";

import { api } from "@/lib/api";
import { getT } from "@/lib/i18n/server";
import { LEVELS } from "@/lib/types";

export default async function LevelSelect() {
  const [t, topics] = await Promise.all([getT(), api.topics()]);

  return (
    <div className="page narrow">
      <h1>{t("theory.title")}</h1>
      <p className="subtitle">{t("theory.subtitle")}</p>
      <div className="grid">
        {LEVELS.map((level) => {
          const inLevel = topics.filter((t) => t.level === level);
          const done = inLevel.filter((t) => t.is_completed).length;
          const body = (
            <>
              <div className="big">{level}</div>
              <div className="label">
                {inLevel.length === 0 ? t("theory.noTopicsYet") : t("theory.completedCount", { done, total: inLevel.length })}
              </div>
            </>
          );
          return inLevel.length === 0 ? (
            <div key={level} className="card disabled">
              {body}
            </div>
          ) : (
            <Link key={level} href={`/theory/${level}`} className="card">
              {body}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
