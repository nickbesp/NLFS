import type { Lang } from "../prefs.ts";
import { en, type MessageKey, type Messages } from "./en.ts";
import { es } from "./es.ts";
import { ru } from "./ru.ts";

export type { MessageKey, Messages };

export type Vars = Record<string, string | number>;
export type TFunction = (key: MessageKey, vars?: Vars) => string;

export const dictionaries: Record<Lang, Messages> = { en, es, ru };

/** Each language's own name, shown the same in every interface language. */
export const LANG_NAMES: Record<Lang, string> = { en: "English", es: "Castellano", ru: "Русский" };

export function format(template: string, vars?: Vars): string {
  if (!vars) return template;
  return template.replace(/\{(\w+)\}/g, (match, name: string) => (name in vars ? String(vars[name]) : match));
}

export function translate(lang: Lang, key: MessageKey, vars?: Vars): string {
  return format(dictionaries[lang][key], vars);
}
