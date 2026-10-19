import Link from "next/link";

import { getT } from "@/lib/i18n/server";

export default async function NotFound() {
  const t = await getT();
  return (
    <div className="page narrow">
      <h1>{t("notFound.title")}</h1>
      <p className="subtitle">{t("notFound.subtitle")}</p>
      <Link href="/" className="button">
        {t("common.backToDashboard")}
      </Link>
    </div>
  );
}
