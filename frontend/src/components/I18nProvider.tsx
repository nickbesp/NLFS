"use client";

// Gives Client Components the interface language chosen in Settings.
import { createContext, useContext } from "react";

import { translate, type TFunction } from "@/lib/i18n";
import type { Lang } from "@/lib/prefs";

const LangContext = createContext<Lang>("en");

export default function I18nProvider({ lang, children }: { lang: Lang; children: React.ReactNode }) {
  return <LangContext.Provider value={lang}>{children}</LangContext.Provider>;
}

export function useLang(): Lang {
  return useContext(LangContext);
}

export function useT(): TFunction {
  const lang = useLang();
  return (key, vars) => translate(lang, key, vars);
}
