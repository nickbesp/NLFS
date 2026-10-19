// Reads the theme/language cookies for Server Components.
import "server-only";

import { cookies } from "next/headers";

import { LANG_COOKIE, parseLang, parseTheme, THEME_COOKIE, type Lang, type Theme } from "../prefs.ts";
import { translate, type TFunction } from "./index.ts";

export async function getPrefs(): Promise<{ theme: Theme; lang: Lang }> {
  const store = await cookies();
  return { theme: parseTheme(store.get(THEME_COOKIE)?.value), lang: parseLang(store.get(LANG_COOKIE)?.value) };
}

export async function getT(): Promise<TFunction> {
  const { lang } = await getPrefs();
  return (key, vars) => translate(lang, key, vars);
}
