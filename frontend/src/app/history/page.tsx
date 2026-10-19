import Link from "next/link";

import { api } from "@/lib/api";
import { getT } from "@/lib/i18n/server";

export default async function HistoryPage() {
  const [t, history] = await Promise.all([getT(), api.history()]);

  return (
    <div className="page narrow">
      <h1>{t("progress.title")}</h1>
      <p className="subtitle">{t("progress.subtitle")}</p>
      {history.length === 0 ? (
        <p>
          {t("progress.empty")} <Link href="/quizzes" className="text-link">{t("progress.takeOne")}</Link>
        </p>
      ) : (
        <div className="panel table-panel">
          <table className="data">
            <thead>
              <tr>
                <th>{t("progress.when")}</th>
                <th>{t("progress.topic")}</th>
                <th>{t("progress.score")}</th>
              </tr>
            </thead>
            <tbody>
              {history.map((h) => (
                <tr key={h.id}>
                  <td>{h.taken_at.slice(0, 16).replace("T", " ")}</td>
                  <td>{h.topic_title ?? "—"}</td>
                  <td className={h.score / h.total >= 0.6 ? "correct" : "wrong"}>
                    {h.score}/{h.total}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
