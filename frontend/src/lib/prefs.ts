// User preferences stored in cookies. No imports, so it runs under plain Node tests.

export const THEMES = ["light", "dark"] as const;
export type Theme = (typeof THEMES)[number];

export const LANGS = ["en", "es", "ru"] as const;
export type Lang = (typeof LANGS)[number];

export const THEME_COOKIE = "nlfs-theme";
export const LANG_COOKIE = "nlfs-lang";

/** The OS theme is deliberately ignored: no cookie means light. */
export function parseTheme(value: string | undefined): Theme {
  return (THEMES as readonly string[]).includes(value ?? "") ? (value as Theme) : "light";
}

export function parseLang(value: string | undefined): Lang {
  return (LANGS as readonly string[]).includes(value ?? "") ? (value as Lang) : "en";
}
