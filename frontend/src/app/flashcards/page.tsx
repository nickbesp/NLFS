import FlashcardReview from "@/components/FlashcardReview";
import { api } from "@/lib/api";
import { getT } from "@/lib/i18n/server";

export default async function FlashcardsPage() {
  const [t, due] = await Promise.all([getT(), api.dueCards()]);

  return (
    <div className="page narrow">
      <h1>{t("flash.title")}</h1>
      <p className="subtitle">{due.length === 0 ? t("flash.none") : t("flash.due", { count: due.length })}</p>
      {due.length > 0 && <FlashcardReview cards={due} />}
    </div>
  );
}
