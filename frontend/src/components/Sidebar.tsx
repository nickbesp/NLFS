"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import ComingSoon from "@/components/ComingSoon";
import Icon from "@/components/Icon";
import { useT } from "@/components/I18nProvider";
import type { MessageKey } from "@/lib/i18n";

type NavItem = { href: string; label: MessageKey; icon: string; highlight?: boolean; badge?: boolean };

const LEARNING: NavItem[] = [
  { href: "/", label: "nav.dashboard", icon: "space_dashboard" },
  { href: "/theory", label: "nav.theory", icon: "menu_book" },
  { href: "/quizzes", label: "nav.quizzes", icon: "quiz" },
  { href: "/flashcards", label: "nav.flashcards", icon: "style", badge: true },
  // Same page as Theory for now; never highlighted so only one item is active.
  { href: "/theory", label: "nav.levels", icon: "stairs", highlight: false },
];

const PERSONAL: NavItem[] = [
  { href: "/history", label: "nav.progress", icon: "trending_up" },
  { href: "/settings", label: "nav.settings", icon: "settings" },
];

function isActive(pathname: string, item: NavItem): boolean {
  if (item.highlight === false) return false;
  return item.href === "/" ? pathname === "/" : pathname === item.href || pathname.startsWith(`${item.href}/`);
}

export default function Sidebar({ dueCount }: { dueCount: number | null }) {
  const t = useT();
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  // Close the mobile overlay after navigating.
  useEffect(() => setOpen(false), [pathname]);

  const renderItem = (item: NavItem) => {
    const active = isActive(pathname, item);
    const showBadge = item.badge && dueCount !== null && dueCount > 0;
    return (
      <li key={item.label}>
        <Link
          href={item.href}
          className={`nav-item${active ? " active" : ""}`}
          aria-current={active ? "page" : undefined}
          title={t(item.label)}
        >
          <Icon name={item.icon} filled={active} />
          <span className="nav-label">{t(item.label)}</span>
          {showBadge && (
            <span className="nav-badge" aria-label={t("nav.dueBadge", { count: dueCount })}>
              {dueCount}
            </span>
          )}
        </Link>
      </li>
    );
  };

  return (
    <>
      <div className="mobile-bar">
        <Link href="/" className="brand">
          <span className="brand-mark">N</span>
          <span className="brand-name">NLFS</span>
        </Link>
        <button type="button" className="icon-button" onClick={() => setOpen(true)} aria-label={t("nav.menu")}>
          <Icon name="menu" />
        </button>
      </div>

      {open && <div className="sidebar-backdrop" onClick={() => setOpen(false)} />}

      <aside className={`sidebar${open ? " open" : ""}`}>
        <div className="sidebar-top">
          <Link href="/" className="brand">
            <span className="brand-mark">N</span>
            <span className="brand-name">NLFS</span>
          </Link>
          <button type="button" className="icon-button sidebar-close" onClick={() => setOpen(false)} aria-label={t("nav.close")}>
            <Icon name="close" />
          </button>
        </div>

        <nav className="sidebar-nav">
          <p className="nav-section">{t("nav.learning")}</p>
          <ul>{LEARNING.map(renderItem)}</ul>
          <p className="nav-section">{t("nav.personal")}</p>
          <ul>{PERSONAL.map(renderItem)}</ul>
        </nav>

        <div className="sidebar-profile">
          <ComingSoon id="profile" compact />
        </div>
      </aside>
    </>
  );
}
