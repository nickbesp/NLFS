"use client";

// Greyed-out stand-in for a part of the Terra design that has no data yet.
// The full list of these lives in src/lib/comingSoon.ts.
import Icon from "@/components/Icon";
import { useT } from "@/components/I18nProvider";
import { comingSoonKeys, type ComingSoonId } from "@/lib/comingSoon";

export default function ComingSoon({
  id,
  compact = false,
  children,
}: {
  id: ComingSoonId;
  /** Small inline variant for tight spots (top bar, sidebar): name + badge, needs-note as tooltip. */
  compact?: boolean;
  children?: React.ReactNode;
}) {
  const t = useT();
  const keys = comingSoonKeys(id);
  const name = t(keys.name);
  const needs = t("coming.needs", { what: t(keys.needs) });

  return (
    <div className={`coming-soon${compact ? " compact" : ""}`} data-coming-soon={id} title={compact ? `${name} — ${needs}` : undefined}>
      {children && (
        <div className="coming-soon-preview" inert aria-hidden="true">
          {children}
        </div>
      )}
      <div className="coming-soon-label">
        <span className="pill pill-amber">
          <Icon name="schedule" />
          {t("coming.badge")}
        </span>
        <strong className="coming-soon-name">{name}</strong>
        {!compact && <span className="coming-soon-needs">{needs}</span>}
      </div>
    </div>
  );
}
