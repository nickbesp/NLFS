"use client";

import { useT } from "@/components/I18nProvider";

export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  const t = useT();
  return (
    <div className="page narrow">
      <div className="error-box">
        <h1>{t("error.title")}</h1>
        <p>{error.message || t("error.fallback")}</p>
        <p className="hint">
          {t("error.hintBefore")} <code>cd backend; .venv\Scripts\python run.py</code>, {t("error.hintAfter")}
        </p>
        <button onClick={reset}>{t("error.retry")}</button>
      </div>
    </div>
  );
}
